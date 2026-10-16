import os

import httpx
import pytest_asyncio
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database.session import get_db
from main import app
from models import Base
from services.cache import CounterCache


@pytest_asyncio.fixture
async def sessions():
    import pytest
    from uuid import uuid4

    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Run tests through Docker Compose")
    schema = f"test_{uuid4().hex}"
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(CreateSchema(schema))
    engine = create_async_engine(
        url, connect_args={"server_settings": {"search_path": schema}}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(DropSchema(schema, cascade=True))
        await admin.dispose()


class FakePublisher:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


@pytest_asyncio.fixture
async def api(sessions):
    publisher = FakePublisher()
    app.state.publisher = publisher
    app.state.counter_cache = CounterCache(None)

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            yield client, publisher, sessions
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def postgres_sessions():
    import pytest

    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Run with Docker Compose test profile")
    engine = create_async_engine(url, pool_size=20, max_overflow=0)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()

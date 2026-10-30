from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.db import ShardedDatabase
from shared.redis_client import create_redis

from app.config import get_settings
from app.routes import counters
from app.rpc import create_server
from app.services.cache import CounterCache
from app.services.counters import CountersService
from app.services.local_cache import LocalCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis = create_redis(settings)
    db = ShardedDatabase(settings.database_urls, pool_size=settings.db_pool_size, max_overflow=0, pool_pre_ping=True)
    app.state.counters = CountersService(
        db,
        CounterCache(redis),
        LocalCache(settings.local_cache_size, settings.local_cache_ttl_seconds),
        settings.liked_by_timeout_seconds,
    )
    grpc_server = create_server(app.state, settings.grpc_port)
    await grpc_server.start()
    try:
        yield
    finally:
        await grpc_server.stop(grace=5)
        await db.dispose()
        await redis.aclose()


app = FastAPI(title="Read Service", lifespan=lifespan)
app.include_router(counters.router)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}

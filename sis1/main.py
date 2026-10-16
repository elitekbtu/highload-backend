from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as PoolTimeoutError

from config import get_settings
from database.session import SessionLocal, engine
from routes.like import router as like_router
from routes.post import router as post_router
from routes.view import router as view_router
from services.cache import CounterCache
from services.publisher import EventPublisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis = Redis.from_url(
        settings.redis_url, decode_responses=True,
        socket_connect_timeout=0.05, socket_timeout=0.05,
    )
    publisher = EventPublisher(settings)
    app.state.counter_cache = CounterCache(redis, settings.counter_cache_ttl_ms)
    app.state.publisher = publisher
    try:
        await publisher.start()
        yield
    finally:
        try:
            await publisher.stop()
        finally:
            await redis.aclose()
            await engine.dispose()


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.include_router(post_router)
app.include_router(like_router)
app.include_router(view_router)


async def database_unavailable(request, exc):
    return JSONResponse(
        status_code=503, content={"detail": "Database unavailable; retry later"},
        headers={"Retry-After": "1"},
    )


app.add_exception_handler(OperationalError, database_unavailable)
app.add_exception_handler(PoolTimeoutError, database_unavailable)
app.add_exception_handler(OSError, database_unavailable)
app.add_exception_handler(TimeoutError, database_unavailable)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.get("/ready", tags=["Health"])
async def ready():
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

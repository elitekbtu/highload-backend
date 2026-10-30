from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.config import get_settings
from app.routes import likes, views
from app.services.dedup import ViewDedup
from app.services.publisher import EventPublisher
from app.services.view_token import ViewTokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    publisher = EventPublisher(settings)
    await publisher.start()
    app.state.publisher = publisher
    app.state.dedup = ViewDedup(redis)
    app.state.view_tokens = ViewTokens(
        settings.view_token_secret, settings.view_token_ttl_seconds, settings.view_min_seconds
    )
    try:
        yield
    finally:
        await publisher.stop()
        await redis.aclose()


app = FastAPI(title="Write Service", lifespan=lifespan)
app.include_router(likes.router)
app.include_router(views.router)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}

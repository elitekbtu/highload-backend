from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.config import get_settings
from app.routes import likes, views
from app.rpc import create_server
from app.services.dedup import ViewDedup
from app.services.publisher import EventBusUnavailable, EventPublisher
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
    grpc_server = create_server(app.state, settings.grpc_port)
    await grpc_server.start()
    try:
        yield
    finally:
        await grpc_server.stop(grace=5)
        await publisher.stop()
        await redis.aclose()


app = FastAPI(title="Write Service", lifespan=lifespan)
app.include_router(likes.router)
app.include_router(views.router)


@app.exception_handler(EventBusUnavailable)
async def event_bus_unavailable(request: Request, exc: EventBusUnavailable) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=503)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from shared.redis_client import create_redis

from app.config import get_settings
from app.container import Container
from app.routes import likes, views
from app.rpc import create_server
from app.services.dedup import ViewDedup
from app.services.lossy_publisher import LossyPublisher
from app.services.publisher import EventBusUnavailable, EventPublisher
from app.services.view_token import ViewTokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis = create_redis(settings)
    publisher = LossyPublisher(settings) if settings.chaos_ack_loss_rate else EventPublisher(settings)
    await publisher.start()
    container = Container(
        settings=settings,
        publisher=publisher,
        dedup=ViewDedup(redis),
        view_tokens=ViewTokens(settings.view_token_secret, settings.view_token_ttl_seconds, settings.view_min_seconds),
    )
    app.state.container = container
    grpc_server = create_server(container)
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

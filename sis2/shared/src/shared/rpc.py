import asyncio
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import grpc

from shared.auth import Unauthorized, user_id_from_header


async def user_id_from_context(context: grpc.aio.ServicerContext, secret: str) -> int:
    authorization = dict(context.invocation_metadata() or ()).get("authorization")
    try:
        return user_id_from_header(authorization if isinstance(authorization, str) else None, secret)
    except Unauthorized as exc:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, str(exc))


async def event_id_from_key(context: grpc.aio.ServicerContext, key: str) -> UUID:
    if not key:
        return uuid4()
    try:
        return UUID(key)
    except ValueError:
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "idempotency_key must be a UUID")


@asynccontextmanager
async def within_deadline(context: grpc.aio.ServicerContext):
    try:
        async with asyncio.timeout(context.time_remaining()):
            yield
    except TimeoutError:
        await context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, "deadline exceeded")

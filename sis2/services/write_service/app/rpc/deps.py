from contextlib import asynccontextmanager

import grpc
from shared.rpc import user_id_from_context, within_deadline

from app.container import Container
from app.services.publisher import EventBusUnavailable


class RpcHandlers:
    container: Container

    async def authorize(self, context: grpc.aio.ServicerContext, post_id: int) -> int:
        user_id = await user_id_from_context(context, self.container.settings.jwt_secret)
        if post_id <= 0:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "post_id must be a positive integer")
        return user_id


@asynccontextmanager
async def publishing(context: grpc.aio.ServicerContext):
    async with within_deadline(context):
        try:
            yield
        except EventBusUnavailable as exc:
            await context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))

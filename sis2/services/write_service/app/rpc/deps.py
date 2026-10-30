import grpc
from shared.rpc import user_id_from_context

from app.config import get_settings


async def get_user_id(context: grpc.aio.ServicerContext) -> int:
    return await user_id_from_context(context, get_settings().jwt_secret)


async def check_post_id(post_id: int, context: grpc.aio.ServicerContext) -> None:
    if post_id <= 0:
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "post_id must be a positive integer")

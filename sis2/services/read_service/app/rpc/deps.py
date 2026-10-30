import grpc
from shared.rpc import user_id_from_context

from app.config import get_settings


async def get_user_id(context: grpc.aio.ServicerContext) -> int:
    return await user_id_from_context(context, get_settings().jwt_secret)

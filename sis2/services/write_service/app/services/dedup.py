import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError
from shared.redis_keys import VIEW_DEDUP_TTL_SECONDS, view_dedup_key

logger = logging.getLogger(__name__)


class ViewDedup:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def first_view(self, post_id: int, user_id: int) -> bool:
        try:
            return bool(await self.redis.set(view_dedup_key(post_id, user_id), 1, nx=True, ex=VIEW_DEDUP_TTL_SECONDS))
        except RedisError:
            logger.warning("view dedup unavailable", exc_info=True)
            return True

    async def forget(self, post_id: int, user_id: int) -> None:
        try:
            await self.redis.delete(view_dedup_key(post_id, user_id))
        except RedisError:
            logger.warning("view dedup unavailable", exc_info=True)

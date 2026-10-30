import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError
from shared.redis_keys import LIKES_FIELD, VIEWS_FIELD, counter_key

from app.services.local_cache import Counters

logger = logging.getLogger(__name__)


class CounterCache:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_many(self, post_ids: list[int]) -> dict[int, Counters]:
        try:
            async with self.redis.pipeline(transaction=False) as pipe:
                for post_id in post_ids:
                    pipe.hmget(counter_key(post_id), LIKES_FIELD, VIEWS_FIELD)
                rows = await pipe.execute()
        except RedisError:
            logger.warning("counter cache unavailable", exc_info=True)
            return {}
        return {
            post_id: Counters(int(likes), int(views))
            for post_id, (likes, views) in zip(post_ids, rows, strict=True)
            if likes is not None and views is not None
        }

    async def fill(self, counters: dict[int, Counters]) -> None:
        try:
            async with self.redis.pipeline(transaction=False) as pipe:
                for post_id, (likes, views) in counters.items():
                    pipe.hsetnx(counter_key(post_id), LIKES_FIELD, likes)
                    pipe.hsetnx(counter_key(post_id), VIEWS_FIELD, views)
                await pipe.execute()
        except RedisError:
            logger.warning("counter cache unavailable", exc_info=True)

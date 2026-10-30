import asyncio
from collections.abc import Iterable
from functools import partial

from shared.db import ShardedDatabase

from app.schemas import PostCounters
from app.services.cache import CounterCache
from app.services.local_cache import Counters, LocalCache
from app.services.queries import load_counters, load_liked


class InvalidPostIds(ValueError):
    pass


def normalize_post_ids(post_ids: Iterable[int], max_posts: int) -> list[int]:
    unique = list(dict.fromkeys(post_ids))
    if not unique or any(not 0 < post_id < 2**63 for post_id in unique):
        raise InvalidPostIds("post_ids must be positive integers")
    if len(unique) > max_posts:
        raise InvalidPostIds(f"at most {max_posts} post_ids per request")
    return unique


class CountersService:
    def __init__(self, db: ShardedDatabase, cache: CounterCache, local: LocalCache, db_timeout: float):
        self.db = db
        self.cache = cache
        self.local = local
        self.db_timeout = db_timeout

    async def get_many(self, post_ids: list[int], user_id: int) -> list[PostCounters]:
        counters, liked = await asyncio.gather(self.counters(post_ids), self.liked_by(user_id, post_ids))
        result = []
        for post_id in post_ids:
            if post_id in counters:
                likes, views = counters[post_id]
                result.append(PostCounters(post_id=post_id, likes=likes, views=views, liked_by_me=liked.get(post_id)))
            else:
                result.append(PostCounters(post_id=post_id, unavailable=True))
        return result

    async def counters(self, post_ids: list[int]) -> dict[int, Counters]:
        counters = self.local.get_many(post_ids)
        missing = [post_id for post_id in post_ids if post_id not in counters]
        if not missing:
            return counters

        found = await self.cache.get_many(missing)
        not_cached = [post_id for post_id in missing if post_id not in found]
        if not_cached:
            from_db = await self.load(not_cached)
            await self.cache.fill(from_db)
            found |= from_db

        self.local.put_many(found)
        return counters | found

    async def load(self, post_ids: list[int]) -> dict[int, Counters]:
        loaded: dict[int, Counters] = {}
        for shard_counters in await self.db.read_shards(post_ids, load_counters, self.db_timeout):
            loaded |= shard_counters
        return loaded

    async def liked_by(self, user_id: int, post_ids: list[int]) -> dict[int, bool]:
        known: dict[int, bool] = {}
        for shard_liked in await self.db.read_shards(post_ids, partial(load_liked, user_id=user_id), self.db_timeout):
            known |= shard_liked
        return known

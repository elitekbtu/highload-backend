import asyncio
import logging
from collections.abc import Iterable
from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel
from shared.db import ShardedDatabase
from shared.models import Like, PostCounter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services.cache import CounterCache
from app.services.local_cache import Counters, LocalCache

logger = logging.getLogger(__name__)


class InvalidPostIds(ValueError):
    pass


def normalize_post_ids(post_ids: Iterable[int], max_posts: int) -> list[int]:
    unique = list(dict.fromkeys(post_ids))
    if not unique or any(not 0 < post_id < 2**63 for post_id in unique):
        raise InvalidPostIds("post_ids must be positive integers")
    if len(unique) > max_posts:
        raise InvalidPostIds(f"at most {max_posts} post_ids per request")
    return unique


class PostCounters(BaseModel):
    post_id: int
    likes: int
    views: int
    liked_by_me: bool
    unavailable: bool = False


class CountersService:
    def __init__(self, db: ShardedDatabase, cache: CounterCache, local: LocalCache, db_timeout: float):
        self.db = db
        self.cache = cache
        self.local = local
        self.db_timeout = db_timeout

    async def get_many(self, post_ids: list[int], user_id: int) -> list[PostCounters]:
        counters, liked = await asyncio.gather(self._counters(post_ids), self._liked_by(user_id, post_ids))
        return [
            PostCounters(
                post_id=post_id,
                likes=counters[post_id][0],
                views=counters[post_id][1],
                liked_by_me=post_id in liked,
            )
            if post_id in counters
            else PostCounters(post_id=post_id, likes=0, views=0, liked_by_me=False, unavailable=True)
            for post_id in post_ids
        ]

    async def _counters(self, post_ids: list[int]) -> dict[int, Counters]:
        counters = self.local.get_many(post_ids)
        missing = [post_id for post_id in post_ids if post_id not in counters]
        if not missing:
            return counters

        found = await self.cache.get_many(missing)
        not_cached = [post_id for post_id in missing if post_id not in found]
        if not_cached:
            from_db = await self._load(not_cached)
            await self.cache.fill(from_db)
            found |= from_db

        self.local.put_many(found)
        return counters | found

    async def _load(self, post_ids: list[int]) -> dict[int, Counters]:
        async def load_shard(engine: AsyncEngine, ids: list[int]) -> dict[int, Counters]:
            stmt = select(PostCounter.post_id, PostCounter.likes_count, PostCounter.views_count).where(
                PostCounter.post_id.in_(ids)
            )
            async with engine.connect() as conn:
                rows = (await conn.execute(stmt)).all()
            return {post_id: (0, 0) for post_id in ids} | {
                row.post_id: (row.likes_count, row.views_count) for row in rows
            }

        loaded: dict[int, Counters] = {}
        for ids, result in await self.db.read_shards(post_ids, load_shard, self.db_timeout):
            if isinstance(result, Exception):
                logger.warning("counters unavailable for %d posts", len(ids), exc_info=result)
            else:
                loaded |= result
        return loaded

    async def _liked_by(self, user_id: int, post_ids: list[int]) -> set[int]:
        async def load_shard(engine: AsyncEngine, ids: list[int]) -> set[int]:
            stmt = select(Like.post_id).where(Like.post_id.in_(ids), Like.user_id == user_id)
            async with engine.connect() as conn:
                return set((await conn.scalars(stmt)).all())

        liked: set[int] = set()
        for ids, result in await self.db.read_shards(post_ids, load_shard, self.db_timeout):
            if isinstance(result, Exception):
                logger.warning("liked_by_me unavailable for %d posts", len(ids), exc_info=result)
            else:
                liked |= result
        return liked


async def get_counters_service(request: Request) -> CountersService:
    return request.app.state.counters


CountersServiceDep = Annotated[CountersService, Depends(get_counters_service)]

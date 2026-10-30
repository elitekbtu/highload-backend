import logging
from collections import Counter

from cachetools import LRUCache
from redis.asyncio import Redis
from shared.db import ShardedDatabase
from shared.events import EventType
from shared.models import Like, PostCounter
from shared.redis_keys import LIKES_FIELD, VIEWS_FIELD, counter_key
from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.batcher import Batch

logger = logging.getLogger(__name__)

CHUNK_SIZE = 5000


class Flusher:
    def __init__(self, db: ShardedDatabase, redis: Redis, flushed_views_size: int):
        self.db = db
        self.redis = redis
        self.pending_views: Counter[int] = Counter()
        self.flushed_views: LRUCache[int, int] = LRUCache(flushed_views_size)

    def forget(self) -> None:
        self.flushed_views.clear()

    async def apply(self, batch: Batch) -> None:
        likes = await self.apply_likes(batch.like_changes) if batch.like_changes else {}
        views = await self.total_views(batch.views) if batch.views else {}
        await self.update_cache(likes, views)
        self.pending_views.update(batch.views)

    async def apply_likes(self, changes: dict[tuple[int, int], EventType]) -> dict[int, int]:
        async def apply_shard(engine: AsyncEngine, post_ids: list[int]) -> dict[int, int]:
            shard_posts = set(post_ids)
            return await write_likes(engine, sorted(item for item in changes.items() if item[0][0] in shard_posts))

        likes: dict[int, int] = {}
        for shard_likes in await self.db.map_shards({post_id for post_id, _ in changes}, apply_shard):
            likes |= shard_likes
        return likes

    async def total_views(self, batch_views: Counter[int]) -> dict[int, int]:
        flushed = {post_id: self.flushed_views[post_id] for post_id in batch_views if post_id in self.flushed_views}
        if missing := [post_id for post_id in batch_views if post_id not in flushed]:
            for shard_views in await self.db.map_shards(missing, load_views):
                flushed |= shard_views
            self.flushed_views.update({post_id: flushed[post_id] for post_id in missing})
        return {post_id: flushed[post_id] + self.pending_views[post_id] + n for post_id, n in batch_views.items()}

    async def update_cache(self, likes: dict[int, int], views: dict[int, int]) -> None:
        async with self.redis.pipeline(transaction=False) as pipe:
            for post_id in likes.keys() | views.keys():
                fields = {LIKES_FIELD: likes.get(post_id), VIEWS_FIELD: views.get(post_id)}
                pipe.hset(counter_key(post_id), mapping={k: v for k, v in fields.items() if v is not None})
            await pipe.execute()

    async def flush_views(self) -> None:
        if not self.pending_views:
            return
        pending, self.pending_views = self.pending_views, Counter()

        async def flush_shard(engine: AsyncEngine, post_ids: list[int]) -> dict[int, int] | Exception:
            try:
                return await write_views(engine, {post_id: pending[post_id] for post_id in sorted(post_ids)})
            except Exception as exc:
                self.pending_views.update({post_id: pending[post_id] for post_id in post_ids})
                return exc

        flushed: dict[int, int] = {}
        errors: list[Exception] = []
        for result in await self.db.map_shards(pending, flush_shard):
            if isinstance(result, Exception):
                errors.append(result)
            else:
                flushed |= result
        self.flushed_views.update(flushed)
        await self.update_cache({}, flushed)
        if errors:
            raise errors[0]
        logger.info("flushed views of %d posts", len(pending))


async def write_likes(engine: AsyncEngine, changes: list[tuple[tuple[int, int], EventType]]) -> dict[int, int]:
    liked = [{"post_id": p, "user_id": u} for (p, u), kind in changes if kind is EventType.LIKE]
    unliked = [(p, u) for (p, u), kind in changes if kind is EventType.UNLIKE]
    delta = Counter({post_id: 0 for (post_id, _), _ in changes})

    async with engine.begin() as conn:
        if liked:
            rows = await conn.scalars(insert(Like).values(liked).on_conflict_do_nothing().returning(Like.post_id))
            delta.update(rows.all())
        if unliked:
            rows = await conn.scalars(
                delete(Like).where(tuple_(Like.post_id, Like.user_id).in_(unliked)).returning(Like.post_id)
            )
            delta.subtract(rows.all())
        stmt = insert(PostCounter).values(
            [{"post_id": post_id, "likes_count": delta[post_id]} for post_id in sorted(delta)]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[PostCounter.post_id],
            set_={"likes_count": PostCounter.likes_count + stmt.excluded.likes_count, "updated_at": func.now()},
        ).returning(PostCounter.post_id, PostCounter.likes_count)
        return {row.post_id: row.likes_count for row in await conn.execute(stmt)}


async def write_views(engine: AsyncEngine, views: dict[int, int]) -> dict[int, int]:
    post_ids = list(views)
    written: dict[int, int] = {}
    async with engine.begin() as conn:
        for start in range(0, len(post_ids), CHUNK_SIZE):
            stmt = insert(PostCounter).values(
                [
                    {"post_id": post_id, "views_count": views[post_id]}
                    for post_id in post_ids[start : start + CHUNK_SIZE]
                ]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[PostCounter.post_id],
                set_={"views_count": PostCounter.views_count + stmt.excluded.views_count, "updated_at": func.now()},
            ).returning(PostCounter.post_id, PostCounter.views_count)
            written |= {row.post_id: row.views_count for row in await conn.execute(stmt)}
    return written


async def load_views(engine: AsyncEngine, post_ids: list[int]) -> dict[int, int]:
    stmt = select(PostCounter.post_id, PostCounter.views_count).where(PostCounter.post_id.in_(post_ids))
    async with engine.connect() as conn:
        rows = (await conn.execute(stmt)).all()
    return {post_id: 0 for post_id in post_ids} | {row.post_id: row.views_count for row in rows}

import logging
from collections import Counter

from redis.asyncio import Redis
from shared.db import ShardedDatabase
from shared.events import EventType
from shared.models import Like, PostCounter
from shared.redis_keys import LIKES_FIELD, OFFSET_FIELD, VIEWS_FIELD, counter_key
from sqlalchemy import delete, func, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.batcher import Batch

logger = logging.getLogger(__name__)

UPDATE_COUNTER = f"""
if redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
if ARGV[1] ~= '' then redis.call('HSET', KEYS[1], '{LIKES_FIELD}', ARGV[1]) end
local applied = tonumber(redis.call('HGET', KEYS[1], '{OFFSET_FIELD}') or '-1')
local views, last = 0, applied
for i = 2, #ARGV do
  local offset = tonumber(ARGV[i])
  if offset > applied then
    views = views + 1
    if offset > last then last = offset end
  end
end
if views > 0 then
  redis.call('HINCRBY', KEYS[1], '{VIEWS_FIELD}', views)
  redis.call('HSET', KEYS[1], '{OFFSET_FIELD}', last)
end
return 1
"""

CHUNK_SIZE = 5000


class Flusher:
    def __init__(self, db: ShardedDatabase, redis: Redis):
        self.db = db
        self.redis = redis
        self.update_counter = redis.register_script(UPDATE_COUNTER)
        self.pending_views: Counter[int] = Counter()

    async def apply(self, batch: Batch) -> None:
        likes = await self.apply_likes(batch.like_changes) if batch.like_changes else {}
        await self.update_cache(likes, batch.view_offsets)
        self.pending_views.update({post_id: len(offsets) for post_id, offsets in batch.view_offsets.items()})

    async def apply_likes(self, changes: dict[tuple[int, int], EventType]) -> dict[int, int]:

        async def apply_shard(engine: AsyncEngine, post_ids: list[int]) -> dict[int, int]:
            shard_posts = set(post_ids)
            shard_changes = sorted((key, kind) for key, kind in changes.items() if key[0] in shard_posts)
            liked = [{"post_id": p, "user_id": u} for (p, u), kind in shard_changes if kind is EventType.LIKE]
            unliked = [(p, u) for (p, u), kind in shard_changes if kind is EventType.UNLIKE]
            delta = Counter({post_id: 0 for post_id in shard_posts})

            async with engine.begin() as conn:
                if liked:
                    rows = await conn.scalars(
                        insert(Like).values(liked).on_conflict_do_nothing().returning(Like.post_id)
                    )
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

        post_ids = {post_id for post_id, _ in changes}
        likes: dict[int, int] = {}
        for shard_likes in await self.db.map_shards(post_ids, apply_shard):
            likes |= shard_likes
        return likes

    async def update_cache(self, likes: dict[int, int], view_offsets: dict[int, list[int]]) -> None:
        async with self.redis.pipeline(transaction=False) as pipe:
            for post_id in likes.keys() | view_offsets.keys():
                likes_value = likes.get(post_id)
                await self.update_counter(
                    keys=[counter_key(post_id)],
                    args=["" if likes_value is None else likes_value, *view_offsets.get(post_id, [])],
                    client=pipe,
                )
            await pipe.execute()

    async def flush_views(self) -> None:
        if not self.pending_views:
            return
        pending, self.pending_views = self.pending_views, Counter()

        async def flush_shard(engine: AsyncEngine, post_ids: list[int]) -> Exception | None:
            post_ids.sort()
            try:
                await write_shard(engine, post_ids)
            except Exception as exc:
                self.pending_views.update({post_id: pending[post_id] for post_id in post_ids})
                return exc
            return None

        async def write_shard(engine: AsyncEngine, post_ids: list[int]) -> None:
            async with engine.begin() as conn:
                for start in range(0, len(post_ids), CHUNK_SIZE):
                    chunk = post_ids[start : start + CHUNK_SIZE]
                    stmt = insert(PostCounter).values(
                        [{"post_id": post_id, "views_count": pending[post_id]} for post_id in chunk]
                    )
                    await conn.execute(
                        stmt.on_conflict_do_update(
                            index_elements=[PostCounter.post_id],
                            set_={
                                "views_count": PostCounter.views_count + stmt.excluded.views_count,
                                "updated_at": func.now(),
                            },
                        )
                    )

        if errors := [error for error in await self.db.map_shards(pending, flush_shard) if error]:
            raise errors[0]
        logger.info("flushed views of %d posts", len(pending))

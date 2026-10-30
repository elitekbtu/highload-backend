from shared.models import Like, PostCounter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services.local_cache import Counters


async def load_counters(engine: AsyncEngine, post_ids: list[int]) -> dict[int, Counters]:
    stmt = select(PostCounter.post_id, PostCounter.likes_count, PostCounter.views_count).where(
        PostCounter.post_id.in_(post_ids)
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(stmt)).all()
    return {post_id: Counters(0, 0) for post_id in post_ids} | {
        row.post_id: Counters(row.likes_count, row.views_count) for row in rows
    }


async def load_liked(engine: AsyncEngine, post_ids: list[int], user_id: int) -> dict[int, bool]:
    stmt = select(Like.post_id).where(Like.post_id.in_(post_ids), Like.user_id == user_id)
    async with engine.connect() as conn:
        liked = set((await conn.scalars(stmt)).all())
    return {post_id: post_id in liked for post_id in post_ids}

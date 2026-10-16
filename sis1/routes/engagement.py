import time
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Post
from schemas.engagement import EngagementAccepted, EngagementEvent, EngagementKind, EngagementRequest
from services.cache import CounterCache
from services.publisher import EventPublisher


async def accept_event(
    kind: EngagementKind,
    obj_in: EngagementRequest,
    db: AsyncSession,
    publisher: EventPublisher,
    cache: CounterCache,
) -> EngagementAccepted:
    if not await cache.post_exists(obj_in.post_id):
        async with db.begin():
            post_id = await db.scalar(select(Post.id).where(Post.id == obj_in.post_id))
        if post_id is None:
            raise HTTPException(404, "Post not found")
        await cache.remember_post(post_id)
    event = EngagementEvent(
        **obj_in.model_dump(), event_id=uuid4(), kind=kind,
        accepted_at_ms=time.time_ns() // 1_000_000,
    )
    await publisher.publish(event)
    return EngagementAccepted(event_id=event.event_id, post_id=event.post_id)

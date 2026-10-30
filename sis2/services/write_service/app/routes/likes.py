from fastapi import APIRouter, Response
from shared.events import CounterEvent, EventType

from app.deps import IdempotencyKey, PostId, UserIdDep
from app.services.publisher import PublisherDep

router = APIRouter(prefix="/api/v1/posts", tags=["likes"])


@router.put("/{post_id}/like", status_code=202)
async def like(post_id: PostId, user_id: UserIdDep, event_id: IdempotencyKey, publisher: PublisherDep) -> Response:
    await publisher.publish(CounterEvent(event_id=event_id, type=EventType.LIKE, post_id=post_id, user_id=user_id))
    return Response(status_code=202)


@router.delete("/{post_id}/like", status_code=202)
async def unlike(post_id: PostId, user_id: UserIdDep, event_id: IdempotencyKey, publisher: PublisherDep) -> Response:
    await publisher.publish(CounterEvent(event_id=event_id, type=EventType.UNLIKE, post_id=post_id, user_id=user_id))
    return Response(status_code=202)

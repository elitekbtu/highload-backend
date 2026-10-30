from uuid import UUID

from shared.events import CounterEvent, EventType

from app.services.dedup import ViewDedup
from app.services.publisher import EventBusUnavailable, EventPublisher


async def count_view(post_id: int, user_id: int, event_id: UUID, dedup: ViewDedup, publisher: EventPublisher) -> bool:
    if not await dedup.first_view(post_id, user_id):
        return False
    try:
        await publisher.publish(CounterEvent(event_id=event_id, type=EventType.VIEW, post_id=post_id, user_id=user_id))
    except EventBusUnavailable:
        await dedup.forget(post_id, user_id)
        raise
    return True

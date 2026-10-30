from collections import Counter
from dataclasses import dataclass, field
from uuid import UUID

from cachetools import LRUCache
from shared.events import CounterEvent, EventType


@dataclass
class Batch:
    like_changes: dict[tuple[int, int], EventType] = field(default_factory=dict)
    views: Counter[int] = field(default_factory=Counter)
    duplicates: int = 0

    @classmethod
    def from_events(cls, events: list[CounterEvent], seen: LRUCache[UUID, bool]) -> "Batch":
        batch = cls()
        for event in events:
            if event.event_id in seen:
                batch.duplicates += 1
                continue
            seen[event.event_id] = True
            if event.type is EventType.VIEW:
                batch.views[event.post_id] += 1
            else:
                batch.like_changes[(event.post_id, event.user_id)] = event.type
        return batch

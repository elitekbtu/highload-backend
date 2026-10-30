from collections import defaultdict
from dataclasses import dataclass, field

from shared.events import CounterEvent, EventType


@dataclass
class Batch:
    like_changes: dict[tuple[int, int], EventType] = field(default_factory=dict)
    view_offsets: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def from_records(cls, records: list[tuple[int, CounterEvent]]) -> "Batch":
        batch = cls()
        for offset, event in records:
            if event.type is EventType.VIEW:
                batch.view_offsets[event.post_id].append(offset)
            else:
                batch.like_changes[(event.post_id, event.user_id)] = event.type
        return batch

from enum import StrEnum
from uuid import UUID, uuid4
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    LIKE = "like"
    UNLIKE = "unlike"
    VIEW = "view"


class CounterEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    type: EventType
    post_id: int
    user_id: int
    timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))

    @property
    def kafka_key(self) -> bytes:
        return str(self.post_id).encode()

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "CounterEvent":
        return cls.model_validate_json(data)

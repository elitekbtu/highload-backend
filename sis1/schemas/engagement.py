from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, PositiveInt, StringConstraints

Username = Annotated[str, StringConstraints(min_length=1, max_length=128, pattern=r"^[^\x00]+$")]
EngagementKind = Literal["like", "view"]


class EngagementRequest(BaseModel):
    username: Username
    post_id: PositiveInt


class EngagementAccepted(BaseModel):
    event_id: UUID
    post_id: int
    status: Literal["accepted"] = "accepted"


class EngagementEvent(EngagementRequest):
    event_id: UUID
    kind: EngagementKind
    accepted_at_ms: int = Field(gt=0)

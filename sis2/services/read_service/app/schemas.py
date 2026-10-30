from pydantic import BaseModel


class PostCounters(BaseModel):
    post_id: int
    likes: int = 0
    views: int = 0
    liked_by_me: bool | None = None
    unavailable: bool = False


class CountersOut(BaseModel):
    counters: list[PostCounters]

from typing import NamedTuple

from cachetools import TTLCache


class Counters(NamedTuple):
    likes: int
    views: int


class LocalCache:
    def __init__(self, size: int, ttl_seconds: float):
        self.cache: TTLCache = TTLCache(maxsize=size, ttl=ttl_seconds)

    def get_many(self, post_ids: list[int]) -> dict[int, Counters]:
        return {post_id: self.cache[post_id] for post_id in post_ids if post_id in self.cache}

    def put_many(self, counters: dict[int, Counters]) -> None:
        self.cache.update(counters)

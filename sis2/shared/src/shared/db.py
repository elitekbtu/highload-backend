import asyncio
from collections.abc import Awaitable, Callable, Iterable

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from shared.sharding import HashRing


def shard_name(url: str) -> str:
    parsed = make_url(url)
    return f"{parsed.host}:{parsed.port or 5432}/{parsed.database}"


class ShardedDatabase:
    def __init__(self, urls: list[str], **engine_kwargs):
        self.engines = [create_async_engine(url, **engine_kwargs) for url in urls]
        self.ring = HashRing([shard_name(url) for url in urls])

    async def map_shards[T](
        self, post_ids: Iterable[int], fn: Callable[[AsyncEngine, list[int]], Awaitable[T]]
    ) -> list[T]:
        groups = self.ring.group(post_ids)
        return await asyncio.gather(*(fn(self.engines[shard], ids) for shard, ids in groups.items()))

    async def dispose(self) -> None:
        await asyncio.gather(*(engine.dispose() for engine in self.engines))

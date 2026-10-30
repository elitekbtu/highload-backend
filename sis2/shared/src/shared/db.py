import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterable

from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from shared.sharding import HashRing

logger = logging.getLogger(__name__)

DB_ERRORS = (SQLAlchemyError, OSError, TimeoutError)
PRIMARY_RETRY_SECONDS = 5.0


def shard_name(url: str) -> str:
    parsed = make_url(url)
    return f"{parsed.host}:{parsed.port or 5432}/{parsed.database}"


class ShardedDatabase:
    def __init__(self, urls: list[str], replica_urls: list[str] | None = None, **engine_kwargs):
        self.engines = [create_async_engine(url, **engine_kwargs) for url in urls]
        self.replicas = [create_async_engine(url, **engine_kwargs) for url in replica_urls or []]
        self.ring = HashRing([shard_name(url) for url in urls])
        self.primary_down_until = [0.0] * len(urls)

    async def map_shards[T](
        self, post_ids: Iterable[int], fn: Callable[[AsyncEngine, list[int]], Awaitable[T]]
    ) -> list[T]:
        groups = self.ring.group(post_ids)
        return await asyncio.gather(*(fn(self.engines[shard], ids) for shard, ids in groups.items()))

    async def read_shards[T](
        self, post_ids: Iterable[int], fn: Callable[[AsyncEngine, list[int]], Awaitable[T]], timeout: float
    ) -> list[T]:
        async def read(shard: int, ids: list[int]) -> T | None:
            for engine in self.read_engines(shard):
                try:
                    async with asyncio.timeout(timeout):
                        return await fn(engine, ids)
                except DB_ERRORS:
                    logger.warning("shard %d read failed for %d posts", shard, len(ids), exc_info=True)
                    if engine is self.engines[shard]:
                        self.primary_down_until[shard] = time.monotonic() + PRIMARY_RETRY_SECONDS
            return None

        groups = self.ring.group(post_ids)
        results = await asyncio.gather(*(read(shard, ids) for shard, ids in groups.items()))
        return [result for result in results if result is not None]

    def read_engines(self, shard: int) -> list[AsyncEngine]:
        replicas = self.replicas[shard : shard + 1]
        if replicas and time.monotonic() < self.primary_down_until[shard]:
            return replicas
        return [self.engines[shard], *replicas]

    async def dispose(self) -> None:
        await asyncio.gather(*(engine.dispose() for engine in self.engines + self.replicas))

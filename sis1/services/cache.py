import asyncio
import json
import logging
import time
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from services.metrics import CACHE

logger = logging.getLogger(__name__)


class CounterCache:
    def __init__(self, client: Redis | None, ttl_ms: int = 300):
        self.client = client
        self.ttl_ms = ttl_ms

    async def post_exists(self, post_id: int) -> bool:
        if self.client is None:
            return False
        try:
            async with asyncio.timeout(0.05):
                return await self.client.get(f"post:exists:v1:{post_id}") == "1"
        except (RedisError, TimeoutError):
            return False

    async def remember_post(self, post_id: int) -> None:
        if self.client is None:
            return
        try:
            async with asyncio.timeout(0.05):
                await self.client.set(f"post:exists:v1:{post_id}", "1", ex=30, nx=True)
        except (RedisError, TimeoutError):
            pass

    async def get(self, post_id: int) -> dict | None:
        if self.client is None:
            return None
        try:
            async with asyncio.timeout(0.05):
                value = await self.client.get(f"counter:v1:{post_id}")
            if value is not None:
                result = json.loads(value)
                if not isinstance(result, dict) or not {"post_id", "content", "likes_count", "views_count"} <= result.keys():
                    raise ValueError("invalid counter cache entry")
                CACHE.labels("hit").inc()
                return result
        except (RedisError, TimeoutError, ValueError):
            CACHE.labels("error").inc()
            logger.debug("Redis cache unavailable", exc_info=True)
        CACHE.labels("miss").inc()
        return None

    async def put(self, post_id: int, value: dict, read_started: float) -> None:
        if self.client is None:
            return
        ttl_ms = self.ttl_ms - int((time.monotonic() - read_started) * 1000)
        if ttl_ms <= 0:
            return
        try:
            async with asyncio.timeout(0.05):
                await self.client.set(
                    f"counter:v1:{post_id}", json.dumps(value), px=ttl_ms, nx=True
                )
        except (RedisError, TimeoutError):
            CACHE.labels("error").inc()
            logger.debug("Redis cache fill skipped", exc_info=True)


async def get_cache(request: Request) -> CounterCache:
    return request.app.state.counter_cache


CacheDep = Annotated[CounterCache, Depends(get_cache)]

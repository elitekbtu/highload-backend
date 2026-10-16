import json
import time

from redis.exceptions import ConnectionError

from services.cache import CounterCache


class FakeRedis:
    def __init__(self, fail=False):
        self.value = None
        self.calls = []
        self.fail = fail

    async def get(self, key):
        if self.fail:
            raise ConnectionError("unavailable")
        return self.value

    async def set(self, key, value, **kwargs):
        if self.fail:
            raise ConnectionError("unavailable")
        self.calls.append((key, value, kwargs))
        self.value = value


async def test_redis_failure_is_a_cache_miss():
    cache = CounterCache(FakeRedis(fail=True))
    assert await cache.get(1) is None
    await cache.put(1, {}, time.monotonic())


async def test_delayed_read_cannot_extend_staleness():
    redis = FakeRedis()
    cache = CounterCache(redis, ttl_ms=300)
    await cache.put(1, {}, time.monotonic() - 1)
    assert not redis.calls


async def test_cache_fill_uses_remaining_ttl_and_does_not_replace_newer_fill():
    redis = FakeRedis()
    cache = CounterCache(redis, ttl_ms=300)
    value = {"post_id": 1, "content": None, "likes_count": 2, "views_count": 3}
    await cache.put(1, value, time.monotonic() - 0.05)
    _, _, options = redis.calls[0]
    assert 1 <= options["px"] <= 250
    assert options["nx"] is True
    assert await cache.get(1) == value


async def test_bad_cache_entry_falls_back_to_database():
    redis = FakeRedis()
    redis.value = json.dumps({"unexpected": "payload"})
    assert await CounterCache(redis).get(1) is None

from redis.asyncio import Redis
from redis.asyncio.sentinel import Sentinel

from shared.settings import RedisSettings


def create_redis(settings: RedisSettings) -> Redis:
    timeouts = {
        "socket_timeout": settings.redis_timeout_seconds,
        "socket_connect_timeout": settings.redis_timeout_seconds,
    }
    if not settings.redis_sentinels:
        return Redis.from_url(settings.redis_url, **timeouts)
    nodes = [node.strip().rsplit(":", 1) for node in settings.redis_sentinels.split(",") if node.strip()]
    sentinel = Sentinel([(host, int(port)) for host, port in nodes], sentinel_kwargs=timeouts, **timeouts)
    return sentinel.master_for(settings.redis_master_name)

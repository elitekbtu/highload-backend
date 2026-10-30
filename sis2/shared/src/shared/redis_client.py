from urllib.parse import urlsplit

from redis.asyncio import Redis
from redis.asyncio.sentinel import Sentinel

from shared.settings import RedisSettings


def create_redis(settings: RedisSettings) -> Redis:
    timeout = settings.redis_timeout_seconds
    url = urlsplit(settings.redis_url)
    nodes = [node.rsplit(":", 1) for node in url.netloc.split(",") if node]
    sentinel = Sentinel(
        [(host, int(port)) for host, port in nodes],
        sentinel_kwargs={"socket_timeout": timeout, "socket_connect_timeout": timeout},
        socket_timeout=timeout,
        socket_connect_timeout=timeout,
    )
    return sentinel.master_for(url.path.strip("/"))

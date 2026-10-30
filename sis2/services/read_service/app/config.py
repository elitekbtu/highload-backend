from functools import lru_cache

from shared.settings import AuthSettings, DatabaseSettings, RedisSettings


class Settings(AuthSettings, DatabaseSettings, RedisSettings):
    db_pool_size: int = 20
    local_cache_ttl_seconds: float = 1.0
    local_cache_size: int = 100_000
    max_batch_posts: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()

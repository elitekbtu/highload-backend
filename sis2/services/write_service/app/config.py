from functools import lru_cache

from shared.settings import AuthSettings, KafkaSettings, RedisSettings


class Settings(AuthSettings, RedisSettings, KafkaSettings):
    view_token_secret: str
    view_token_ttl_seconds: int = 3600
    view_min_seconds: float = 2.0
    publish_timeout_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

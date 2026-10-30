from functools import lru_cache

from shared.settings import DatabaseSettings, KafkaSettings, RedisSettings


class Settings(DatabaseSettings, RedisSettings, KafkaSettings):
    kafka_group_id: str = "aggregator"
    kafka_topic_partitions: int = 12
    db_pool_size: int = 5
    batch_window_seconds: float = 1.0
    batch_max_events: int = 10_000
    flush_interval_seconds: float = 10.0
    retry_backoff_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

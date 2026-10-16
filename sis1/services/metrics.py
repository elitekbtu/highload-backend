from prometheus_client import Counter, Gauge, Histogram

ACCEPTED = Counter("counter_events_accepted_total", "Events acknowledged by Kafka", ["kind"])
APPLIED = Counter("counter_events_applied_total", "New unique interactions", ["kind"])
DUPLICATES = Counter("counter_events_duplicate_total", "Duplicate interactions", ["kind"])
REJECTED = Counter("counter_events_rejected_total", "Invalid or orphaned events")
CACHE = Counter("counter_cache_total", "Counter cache operations", ["result"])
BATCH_SECONDS = Histogram("counter_batch_seconds", "PostgreSQL batch transaction duration")
EVENT_AGE = Histogram(
    "counter_event_apply_seconds",
    "Time from API acceptance to PostgreSQL commit; cache TTL adds extra delay",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 1.5, 2, 5, 30),
)
LAG = Gauge("counter_consumer_lag_records", "Fetched partition backlog", ["partition"])

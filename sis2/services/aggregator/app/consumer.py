import asyncio
import logging

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from pydantic import ValidationError
from shared.events import CounterEvent

from app.config import Settings

logger = logging.getLogger(__name__)


async def ensure_topic(settings: Settings) -> None:
    admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    await admin.start()
    try:
        if settings.kafka_topic not in await admin.list_topics():
            await admin.create_topics(
                [NewTopic(settings.kafka_topic, settings.kafka_topic_partitions, replication_factor=settings.kafka_replication_factor)]
            )
    finally:
        await admin.close()


def create_consumer(settings: Settings) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )


async def poll_batch(consumer: AIOKafkaConsumer, window_seconds: float, max_events: int) -> list[CounterEvent]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + window_seconds
    events: list[CounterEvent] = []
    while len(events) < max_events and (remaining := deadline - loop.time()) > 0:
        records = await consumer.getmany(timeout_ms=int(remaining * 1000), max_records=max_events - len(events))
        for messages in records.values():
            for message in messages:
                try:
                    events.append(CounterEvent.from_bytes(message.value or b""))
                except ValidationError:
                    logger.warning("skip malformed event %s:%s", message.partition, message.offset)
    return events

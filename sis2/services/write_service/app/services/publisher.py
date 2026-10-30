import asyncio
import logging
import random
from typing import Annotated

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from fastapi import Depends, Request
from shared.events import CounterEvent

from app.config import Settings

logger = logging.getLogger(__name__)


class EventBusUnavailable(Exception):
    pass


class EventPublisher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            enable_idempotence=True,
            acks="all",
            linger_ms=5,
        )

    async def start(self) -> None:
        async with asyncio.timeout(30):
            await self.producer.start()

    async def stop(self) -> None:
        try:
            async with asyncio.timeout(5):
                await self.producer.stop()
        except TimeoutError:
            logger.warning("Kafka producer shutdown timed out")

    async def publish(self, event: CounterEvent) -> None:
        try:
            async with asyncio.timeout(self.settings.publish_timeout_seconds):
                await self.producer.send_and_wait(self.settings.kafka_topic, event.to_bytes(), key=event.kafka_key)
        except (KafkaError, TimeoutError) as exc:
            raise EventBusUnavailable("event bus unavailable, retry later") from exc
        if random.random() < self.settings.chaos_ack_loss_rate:
            raise EventBusUnavailable("simulated lost ack, retry later")


async def get_publisher(request: Request) -> EventPublisher:
    return request.app.state.publisher


PublisherDep = Annotated[EventPublisher, Depends(get_publisher)]

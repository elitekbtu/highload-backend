import asyncio
import logging
from typing import Annotated

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from fastapi import Depends, HTTPException, Request

from config import AppConfig
from schemas.engagement import EngagementEvent
from services.metrics import ACCEPTED

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, settings: AppConfig):
        self.settings = settings
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            enable_idempotence=True,
            acks="all",
            linger_ms=5,
            compression_type="lz4",
        )
        self.inflight = 0

    async def start(self) -> None:
        async with asyncio.timeout(30):
            await self.producer.start()

    async def stop(self) -> None:
        try:
            async with asyncio.timeout(5):
                await self.producer.stop()
        except TimeoutError:
            logger.warning("Kafka producer shutdown timed out")

    async def publish(self, event: EngagementEvent) -> None:
        if self.inflight >= self.settings.max_inflight_publishes:
            raise HTTPException(429, "Too many pending events", headers={"Retry-After": "1"})
        self.inflight += 1
        try:
            async with asyncio.timeout(self.settings.publish_timeout_seconds):
                await self.producer.send_and_wait(
                    self.settings.kafka_topic,
                    event.model_dump_json().encode(),
                    key=f"{event.post_id}:{event.username}".encode(),
                )
        except (KafkaError, TimeoutError) as exc:
            raise HTTPException(503, "Kafka acknowledgment unavailable; retry safely") from exc
        finally:
            self.inflight -= 1
        ACCEPTED.labels(event.kind).inc()


async def get_publisher(request: Request) -> EventPublisher:
    return request.app.state.publisher


PublisherDep = Annotated[EventPublisher, Depends(get_publisher)]

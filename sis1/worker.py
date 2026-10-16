import asyncio
import base64
import json
import logging
import signal
import time

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import CommitFailedError
from prometheus_client import start_http_server
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from config import get_settings
from database.session import SessionLocal, engine
from schemas.engagement import EngagementEvent
from services.engagements import apply_events
from services.metrics import APPLIED, BATCH_SECONDS, DUPLICATES, EVENT_AGE, LAG, REJECTED

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stopping.set)
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        enable_auto_commit=False,
        auto_offset_reset=settings.kafka_auto_offset_reset,
        max_poll_records=settings.worker_batch_size,
        max_poll_interval_ms=300_000,
    )
    dlq = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        enable_idempotence=True, acks="all",
    )
    start_http_server(settings.worker_metrics_port)
    try:
        await dlq.start()
        await consumer.start()
        while not stopping.is_set():
            batches = await consumer.getmany(
                timeout_ms=settings.worker_poll_ms,
                max_records=settings.worker_batch_size,
            )
            if not batches:
                continue
            events = []
            malformed = []
            offsets = {}
            for tp, messages in batches.items():
                offsets[tp] = messages[-1].offset + 1
                for message in messages:
                    try:
                        events.append(EngagementEvent.model_validate_json(message.value))
                    except ValidationError:
                        malformed.append({
                            "topic": tp.topic, "partition": tp.partition,
                            "offset": message.offset, "reason": "invalid event schema",
                            "payload_base64": base64.b64encode(message.value or b"").decode(),
                        })
            backoff = 0.1
            while True:
                try:
                    started = time.monotonic()
                    async with SessionLocal.begin() as session:
                        result = await apply_events(session, events)
                    BATCH_SECONDS.observe(time.monotonic() - started)
                    break
                except (SQLAlchemyError, OSError, TimeoutError):
                    logger.exception("Batch rolled back; offsets remain uncommitted")
                    if stopping.is_set():
                        return
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 2)

            dead_letters = malformed + [
                {"reason": "post no longer exists", "event": event.model_dump(mode="json")}
                for event in result.rejected
            ]
            for letter in dead_letters:
                await dlq.send_and_wait(settings.kafka_dlq_topic, json.dumps(letter).encode())
                REJECTED.inc()
            for kind in ("like", "view"):
                APPLIED.labels(kind).inc(result.inserted[kind])
                DUPLICATES.labels(kind).inc(result.duplicates[kind])
            rejected_ids = {e.event_id for e in result.rejected}
            for event in events:
                if event.event_id not in rejected_ids:
                    EVENT_AGE.observe(max(0, time.time() - event.accepted_at_ms / 1000))
            try:
                await consumer.commit(offsets)
            except CommitFailedError:
                logger.warning("Partitions reassigned after DB commit; replay is safe")
            for tp, next_offset in offsets.items():
                highwater = consumer.highwater(tp)
                if highwater is not None:
                    LAG.labels(str(tp.partition)).set(max(0, highwater - next_offset))
    finally:
        await consumer.stop()
        try:
            async with asyncio.timeout(5):
                await dlq.stop()
        except TimeoutError:
            logger.warning("DLQ producer shutdown timed out")
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())

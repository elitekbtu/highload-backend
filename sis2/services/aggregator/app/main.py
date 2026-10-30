import asyncio
import logging
import signal
import time
from functools import partial

from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener
from redis.asyncio import Redis
from shared.db import ShardedDatabase

from app.batcher import Batch
from app.config import get_settings
from app.consumer import create_consumer, ensure_topic, poll_batch
from app.flusher import Flusher

logger = logging.getLogger("aggregator")


async def checkpoint(flusher: Flusher, consumer: AIOKafkaConsumer) -> None:
    await flusher.flush_views()
    await consumer.commit()


class CheckpointOnRevoke(ConsumerRebalanceListener):
    def __init__(self, flusher: Flusher, consumer: AIOKafkaConsumer):
        self.flusher = flusher
        self.consumer = consumer

    async def on_partitions_revoked(self, revoked) -> None:
        if revoked:
            await checkpoint(self.flusher, self.consumer)

    async def on_partitions_assigned(self, assigned) -> None:
        pass


async def retry(action, backoff_seconds: float) -> None:
    while True:
        try:
            return await action()
        except Exception:
            logger.exception("retrying in %.1fs", backoff_seconds)
            await asyncio.sleep(backoff_seconds)


async def run() -> None:
    settings = get_settings()
    await ensure_topic(settings)
    db = ShardedDatabase(settings.database_urls, pool_size=settings.db_pool_size, pool_pre_ping=True)
    redis = Redis.from_url(settings.redis_url)
    flusher = Flusher(db, redis)
    consumer = create_consumer(settings)
    consumer.subscribe([settings.kafka_topic], listener=CheckpointOnRevoke(flusher, consumer))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await consumer.start()
    last_flush = time.monotonic()
    try:
        while not stop.is_set():
            records = await poll_batch(consumer, settings.batch_window_seconds, settings.batch_max_events)
            if records:
                batch = Batch.from_records(records)
                await retry(partial(flusher.apply, batch), settings.retry_backoff_seconds)
            if time.monotonic() - last_flush >= settings.flush_interval_seconds:
                await retry(partial(checkpoint, flusher, consumer), settings.retry_backoff_seconds)
                last_flush = time.monotonic()
    finally:
        try:
            await checkpoint(flusher, consumer)
        except Exception:
            logger.exception("final checkpoint failed")
        await consumer.stop()
        await redis.aclose()
        await db.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(run())

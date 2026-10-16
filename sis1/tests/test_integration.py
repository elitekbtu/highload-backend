import asyncio
import os
import time
from uuid import uuid4

import httpx
import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition
from sqlalchemy import func, select

from models import Like, Post, PostCounter, User, View
from services.engagements import apply_events
from config import get_settings
from tests.test_engagements import make_event

pytestmark = pytest.mark.integration


async def test_postgres_concurrent_first_user_and_retries(postgres_sessions):
    name = f"concurrent-{uuid4()}"
    async with postgres_sessions.begin() as session:
        post = Post(content="concurrent test")
        session.add(post)
        await session.flush()
        post_id = post.id

    async def write(kind):
        async with postgres_sessions.begin() as session:
            return await apply_events(session, [make_event(post_id, kind, name)])

    await asyncio.gather(*(write("like" if index % 2 else "view") for index in range(20)))
    async with postgres_sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User).where(User.username == name)) == 1
        for model in (Like, View):
            assert await session.scalar(select(func.count()).select_from(model).where(model.post_id == post_id)) == 1
        totals = (await session.execute(select(
            func.sum(PostCounter.likes_count), func.sum(PostCounter.views_count)
        ).where(PostCounter.post_id == post_id))).one()
        assert totals == (1, 1)


async def test_real_kafka_worker_and_cache():
    base_url = os.getenv("TEST_API_URL")
    if not base_url:
        pytest.skip("Run with Docker Compose test profile")
    async with httpx.AsyncClient(base_url=base_url, timeout=5) as client:
        post = (await client.post("/post/", json={"content": "pipeline test"})).json()
        post_id = post["id"]
        name = f"pipeline-{uuid4()}"
        payload = {"post_id": post_id, "username": name}
        assert (await client.post("/view", json=payload)).status_code == 202
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            counts = (await client.get(f"/post/{post_id}")).json()
            if counts["views_count"] == 1:
                break
            await asyncio.sleep(0.05)
        else:
            pytest.fail("Worker did not consume Kafka events")
        started = time.monotonic()
        responses = await asyncio.gather(*(
            client.post(path, json=payload)
            for path in ["/like", "/view"] * 10
        ))
        assert all(response.status_code == 202 for response in responses)
        deadline = started + 2
        while time.monotonic() < deadline:
            counts = (await client.get(f"/post/{post_id}")).json()
            if counts["likes_count"] == counts["views_count"] == 1:
                break
            await asyncio.sleep(0.03)
        else:
            pytest.fail(f"Freshness exceeded 2 seconds: {counts}")
        await asyncio.sleep(0.4)
        final = (await client.get(f"/post/{post_id}")).json()
        assert final["likes_count"] == final["views_count"] == 1


async def test_malformed_kafka_record_reaches_dlq_without_blocking_worker():
    base_url = os.getenv("TEST_API_URL")
    if not base_url:
        pytest.skip("Run with Docker Compose test profile")
    settings = get_settings()
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers, enable_idempotence=True
    )
    consumer = AIOKafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers, enable_auto_commit=False
    )
    payload = f"not-json-{uuid4()}".encode()
    assigned = [TopicPartition(settings.kafka_dlq_topic, part) for part in range(3)]
    consumer.assign(assigned)
    try:
        await producer.start()
        await consumer.start()
        await consumer.seek_to_end(*assigned)
        await producer.send_and_wait(settings.kafka_topic, payload, key=payload)
        import base64
        import json

        deadline = time.monotonic() + 10
        found = False
        while time.monotonic() < deadline and not found:
            batches = await consumer.getmany(timeout_ms=100)
            found = any(
                base64.b64decode(json.loads(message.value).get("payload_base64", "")) == payload
                for messages in batches.values() for message in messages
            )
        assert found, "Malformed record was not delivered to DLQ"
        async with httpx.AsyncClient(base_url=base_url, timeout=5) as client:
            post = (await client.post("/post/", json={})).json()
            response = await client.post("/view", json={"post_id": post["id"], "username": f"after-dlq-{uuid4()}"})
            assert response.status_code == 202
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                counts = (await client.get(f"/post/{post['id']}")).json()
                if counts["views_count"] == 1:
                    break
                await asyncio.sleep(0.03)
            else:
                pytest.fail("Worker did not resume after malformed record")
    finally:
        await consumer.stop()
        await producer.stop()

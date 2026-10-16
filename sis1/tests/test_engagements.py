import time
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from models import Like, Post, PostCounter, User, View
from schemas.engagement import EngagementEvent
from services.engagements import apply_events


def make_event(post_id, kind="like", username="alice"):
    return EngagementEvent(
        post_id=post_id, username=username, kind=kind,
        event_id=uuid4(), accepted_at_ms=time.time_ns() // 1_000_000,
    )


async def create_post(sessions):
    async with sessions.begin() as session:
        post = Post(content="test")
        session.add(post)
        await session.flush()
        return post.id


async def totals(sessions, post_id):
    async with sessions() as session:
        return (await session.execute(select(
            func.coalesce(func.sum(PostCounter.likes_count), 0),
            func.coalesce(func.sum(PostCounter.views_count), 0),
        ).where(PostCounter.post_id == post_id))).one()


async def test_dedup_is_by_user_post_and_kind_not_event_id(sessions):
    post_id = await create_post(sessions)
    events = [make_event(post_id), make_event(post_id), make_event(post_id, "view"),
              make_event(post_id, "view"), make_event(post_id, username="bob")]
    async with sessions.begin() as session:
        result = await apply_events(session, events)
    assert result.inserted == {"like": 2, "view": 1}
    assert result.duplicates == {"like": 1, "view": 1}
    assert await totals(sessions, post_id) == (2, 1)


async def test_replay_after_db_commit_does_not_increment_again(sessions):
    post_id = await create_post(sessions)
    events = [make_event(post_id), make_event(post_id, "view")]
    for _ in range(3):
        async with sessions.begin() as session:
            await apply_events(session, events)
    assert await totals(sessions, post_id) == (1, 1)
    async with sessions() as session:
        for model in (Like, View, User):
            assert await session.scalar(select(func.count()).select_from(model)) == 1


async def test_interaction_and_counter_roll_back_together(sessions):
    post_id = await create_post(sessions)
    with pytest.raises(RuntimeError):
        async with sessions.begin() as session:
            await apply_events(session, [make_event(post_id)])
            raise RuntimeError("simulate worker crash before commit")
    assert await totals(sessions, post_id) == (0, 0)
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Like)) == 0
        assert await session.scalar(select(func.count()).select_from(User)) == 0


async def test_missing_post_does_not_block_valid_events(sessions):
    post_id = await create_post(sessions)
    missing = make_event(999999, username="missing")
    async with sessions.begin() as session:
        result = await apply_events(session, [make_event(post_id), missing])
    assert result.rejected == [missing]
    assert await totals(sessions, post_id) == (1, 0)
    async with sessions() as session:
        assert await session.scalar(select(User).where(User.username == "missing")) is None


async def test_empty_batch(sessions):
    async with sessions.begin() as session:
        result = await apply_events(session, [])
    assert not result.inserted and not result.rejected


async def test_same_user_counts_once_on_each_post(sessions):
    first, second = await create_post(sessions), await create_post(sessions)
    async with sessions.begin() as session:
        await apply_events(session, [make_event(first), make_event(second)])
    assert await totals(sessions, first) == (1, 0)
    assert await totals(sessions, second) == (1, 0)

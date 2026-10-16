from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Like, Post, PostCounter, User, View
from models.counter import COUNTER_STRIPES
from schemas.engagement import EngagementEvent


@dataclass
class BatchResult:
    inserted: Counter = field(default_factory=Counter)
    duplicates: Counter = field(default_factory=Counter)
    rejected: list[EngagementEvent] = field(default_factory=list)


async def apply_events(db: AsyncSession, events: list[EngagementEvent]) -> BatchResult:
    result = BatchResult()
    if not events:
        return result
    existing_posts = set(await db.scalars(select(Post.id).where(Post.id.in_({e.post_id for e in events}))))
    result.rejected = [e for e in events if e.post_id not in existing_posts]
    events = [e for e in events if e.post_id in existing_posts]
    if not events:
        return result

    names = sorted({e.username for e in events})
    await db.execute(
        insert(User).values([{"username": name} for name in names])
        .on_conflict_do_nothing(index_elements=[User.username])
    )
    users = dict((await db.execute(select(User.username, User.id).where(User.username.in_(names)))).all())
    increments = defaultdict(lambda: {"likes_count": 0, "views_count": 0})

    for kind, model, column in (("like", Like, "likes_count"), ("view", View, "views_count")):
        incoming = [e for e in events if e.kind == kind]
        rows = sorted({(e.post_id, users[e.username]) for e in incoming})
        if not rows:
            continue
        inserted = (await db.execute(
            insert(model).values([{"post_id": post, "user_id": user} for post, user in rows])
            .on_conflict_do_nothing(index_elements=[model.post_id, model.user_id])
            .returning(model.post_id, model.user_id)
        )).all()
        result.inserted[kind] = len(inserted)
        result.duplicates[kind] = len(incoming) - len(inserted)
        for post_id, user_id in inserted:
            increments[(post_id, user_id % COUNTER_STRIPES)][column] += 1

    if increments:
        stmt = insert(PostCounter).values([
            {"post_id": post, "stripe": stripe, **counts}
            for (post, stripe), counts in sorted(increments.items())
        ])
        await db.execute(stmt.on_conflict_do_update(
            index_elements=[PostCounter.post_id, PostCounter.stripe],
            set_={
                "likes_count": PostCounter.likes_count + stmt.excluded.likes_count,
                "views_count": PostCounter.views_count + stmt.excluded.views_count,
            },
        ))
    return result

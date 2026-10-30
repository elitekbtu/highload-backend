from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.deps import ContainerDep, PostId, UserIdDep
from app.schemas import CountersOut, PostCounters
from app.services.counters import InvalidPostIds, normalize_post_ids

router = APIRouter(prefix="/api/v1", tags=["counters"])


def parse_post_ids(raw: str, max_posts: int) -> list[int]:
    try:
        post_ids = [int(part) for part in raw.split(",") if part.strip()]
    except ValueError as exc:
        raise HTTPException(400, "post_ids must be comma separated integers") from exc
    try:
        return normalize_post_ids(post_ids, max_posts)
    except InvalidPostIds as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/posts/{post_id}/counters")
async def post_counters(post_id: PostId, user_id: UserIdDep, container: ContainerDep) -> PostCounters:
    [counters] = await container.counters.get_many([post_id], user_id)
    return counters


@router.get("/counters")
async def many_counters(
    post_ids: Annotated[str, Query(description="comma separated, e.g. 777,778,779")],
    user_id: UserIdDep,
    container: ContainerDep,
) -> CountersOut:
    ids = parse_post_ids(post_ids, container.settings.max_batch_posts)
    return CountersOut(counters=await container.counters.get_many(ids, user_id))

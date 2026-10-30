from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.deps import PostId, UserIdDep
from app.services.counters import CountersServiceDep, PostCounters

router = APIRouter(prefix="/api/v1", tags=["counters"])


class CountersOut(BaseModel):
    counters: list[PostCounters]


def parse_post_ids(raw: str) -> list[int]:
    try:
        post_ids = list(dict.fromkeys(int(part) for part in raw.split(",") if part.strip()))
    except ValueError as exc:
        raise HTTPException(400, "post_ids must be comma separated integers") from exc
    if not post_ids or any(not 0 < post_id < 2**63 for post_id in post_ids):
        raise HTTPException(400, "post_ids must be positive integers")
    if len(post_ids) > get_settings().max_batch_posts:
        raise HTTPException(400, f"at most {get_settings().max_batch_posts} post_ids per request")
    return post_ids


@router.get("/posts/{post_id}/counters")
async def post_counters(post_id: PostId, user_id: UserIdDep, service: CountersServiceDep) -> PostCounters:
    [counters] = await service.get_many([post_id], user_id)
    return counters


@router.get("/counters")
async def many_counters(
    post_ids: Annotated[str, Query(description="comma separated, e.g. 777,778,779")],
    user_id: UserIdDep,
    service: CountersServiceDep,
) -> CountersOut:
    return CountersOut(counters=await service.get_many(parse_post_ids(post_ids), user_id))

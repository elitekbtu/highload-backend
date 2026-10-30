from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.deps import PostId, UserIdDep
from app.services.counters import CountersServiceDep, InvalidPostIds, PostCounters, normalize_post_ids

router = APIRouter(prefix="/api/v1", tags=["counters"])


class CountersOut(BaseModel):
    counters: list[PostCounters]


def parse_post_ids(raw: str) -> list[int]:
    try:
        post_ids = [int(part) for part in raw.split(",") if part.strip()]
    except ValueError as exc:
        raise HTTPException(400, "post_ids must be comma separated integers") from exc
    try:
        return normalize_post_ids(post_ids, get_settings().max_batch_posts)
    except InvalidPostIds as exc:
        raise HTTPException(400, str(exc)) from exc


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

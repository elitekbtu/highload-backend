from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from shared.events import CounterEvent, EventType

from app.deps import PostId, UserIdDep
from app.services.dedup import DedupDep
from app.services.publisher import PublisherDep
from app.services.view_token import InvalidViewToken, ViewTokensDep

router = APIRouter(prefix="/api/v1/posts", tags=["views"])


class ViewStartedOut(BaseModel):
    view_token: str


class ViewFinishedIn(BaseModel):
    view_token: str


@router.post("/{post_id}/view_started")
async def view_started(post_id: PostId, user_id: UserIdDep, tokens: ViewTokensDep) -> ViewStartedOut:
    return ViewStartedOut(view_token=tokens.issue(post_id, user_id))


@router.post("/{post_id}/view_finished", status_code=202, responses={200: {"description": "Already counted"}})
async def view_finished(
    post_id: PostId,
    body: ViewFinishedIn,
    user_id: UserIdDep,
    tokens: ViewTokensDep,
    dedup: DedupDep,
    publisher: PublisherDep,
) -> Response:
    try:
        tokens.verify(body.view_token, post_id, user_id)
    except InvalidViewToken as exc:
        raise HTTPException(400, str(exc)) from exc

    if not await dedup.first_view(post_id, user_id):
        return Response(status_code=200)
    try:
        await publisher.publish(CounterEvent(type=EventType.VIEW, post_id=post_id, user_id=user_id))
    except HTTPException:
        await dedup.forget(post_id, user_id)
        raise
    return Response(status_code=202)

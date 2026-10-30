from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.deps import ContainerDep, IdempotencyKey, PostId, UserIdDep
from app.services.view_token import InvalidViewToken
from app.services.views import count_view

router = APIRouter(prefix="/api/v1/posts", tags=["views"])


class ViewStartedOut(BaseModel):
    view_token: str


class ViewFinishedIn(BaseModel):
    view_token: str


@router.post("/{post_id}/view_started")
async def view_started(post_id: PostId, user_id: UserIdDep, container: ContainerDep) -> ViewStartedOut:
    return ViewStartedOut(view_token=container.view_tokens.issue(post_id, user_id))


@router.post("/{post_id}/view_finished", status_code=202, responses={200: {"description": "Already counted"}})
async def view_finished(
    post_id: PostId,
    body: ViewFinishedIn,
    user_id: UserIdDep,
    event_id: IdempotencyKey,
    container: ContainerDep,
) -> Response:
    try:
        container.view_tokens.verify(body.view_token, post_id, user_id)
    except InvalidViewToken as exc:
        raise HTTPException(400, str(exc)) from exc

    counted = await count_view(post_id, user_id, event_id, container.dedup, container.publisher)
    return Response(status_code=202 if counted else 200)

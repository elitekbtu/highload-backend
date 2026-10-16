from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND
from schemas.view import ViewRequest, ViewResponse

from database.session import SessionDB
from models import View, Post, User

router = APIRouter(prefix="/view", tags=["View"])


@router.post(
    "",
    response_model=ViewResponse,
    status_code=HTTP_201_CREATED,
)
def post_view(
    obj_in: ViewRequest,
    db: SessionDB,
):
    post = db.get(Post, obj_in.post_id)
    if post is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    user = db.scalar(select(User).where(User.username == obj_in.username))
    if user is None:
        user = User(username=obj_in.username)
        db.add(user)
        db.flush()

    view = View(
        post_id=post.id,
        user_id=user.id,
    )
    db.add(view)
    db.commit()
    db.refresh(view)

    return ViewResponse.model_validate(view)

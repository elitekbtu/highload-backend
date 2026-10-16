from fastapi import APIRouter, HTTPException


from sqlalchemy import select
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from database.session import SessionDB
from models import Like, Post, User
from schemas.like import LikeRequest, LikeResponse


router = APIRouter(prefix="/like", tags=["Like"])



@router.post(
    "",
    response_model=LikeResponse,
    status_code=HTTP_201_CREATED,
)
def post_like(obj_in: LikeRequest, db: SessionDB):
    post = db.get(Post, obj_in.post_id)
    if post is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    user = db.scalar(
        select(User).where(User.username == obj_in.username)
    )

    if user is None:
        user = User(username=obj_in.username)
        db.add(user)
        db.flush()

    like = Like(
        post_id=post.id,
        user_id=user.id,
    )
    db.add(like)
    db.commit()
    db.refresh(like)

    return LikeResponse.model_validate(like)

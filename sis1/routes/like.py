from fastapi import APIRouter, HTTPException
from schemas.like import LikeRequest, LikeResponse


from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from database.session import SessionDB
from models import Like
from models import Post

router = APIRouter(prefix="/like", tags=["Like"])


@router.post(
    "",
    response_model=LikeResponse,
    status_code=HTTP_201_CREATED,
)
def post_like(
    obj_in: LikeRequest,
    db: SessionDB,
):

    post = db.get(Post, obj_in.post_id)
    if post is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    data = obj_in.model_dump()
    like = Like(**data)
    db.add(like)
    db.commit()
    db.refresh(like)

    response = LikeResponse.model_validate(like)
    return response

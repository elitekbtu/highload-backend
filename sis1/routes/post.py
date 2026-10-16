from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from sqlalchemy import select, func
from schemas.post import PostResponse, PostRequest, PostDetailResponse

from database.session import SessionDB
from models import Post
from models import Like
from models import View

router = APIRouter(prefix="/post", tags=["Post"])


@router.post(
    "/",
    response_model=PostResponse,
    status_code=HTTP_201_CREATED,
)
def create_post(
    obj_in: PostRequest,
    db: SessionDB,
):
    data = obj_in.model_dump()
    post = Post(**data)
    db.add(post)
    db.commit()
    db.refresh(post)
    response = PostResponse.model_validate(post)
    return response


@router.get(
    "/",
    response_model=list[PostResponse],
    status_code=HTTP_200_OK,
)
def get_posts(db: SessionDB):
    stmt = select(Post)
    posts = db.scalars(stmt).all()
    return posts


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse,
    status_code=HTTP_200_OK,
)
def get_post(
    post_id: int,
    db: SessionDB,
):
    stmt = select(
        Post.id.label("post_id"),
        Post.content,
        (
            select(func.count(Like.id))
            .where(Like.post_id == Post.id)
            .scalar_subquery(),
        ).label("likes_count"),
        (
            select(func.count(View.id))
            .where(View.post_id == Post.id)
            .scalar_subquery(),
        ).label("views_count"),
    ).where(Post.id == post_id)

    result = db.execute(stmt).mappings().one_or_none()

    if result is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return result

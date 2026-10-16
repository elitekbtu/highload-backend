from fastapi import APIRouter
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from sqlalchemy import select

from schemas.post import PostResponse, PostRequest

from database.session import SessionDB
from models import Post

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
    response_model=PostResponse,
    status_code=HTTP_200_OK,
)
def get_post():
    pass

import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select

from database.session import SessionDB
from models import Post, PostCounter
from schemas.post import PostDetailResponse, PostRequest, PostResponse
from services.cache import CacheDep, CounterCache

router = APIRouter(prefix="/post", tags=["Post"])


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(obj_in: PostRequest, db: SessionDB, cache: CacheDep):
    post = Post(**obj_in.model_dump())
    db.add(post)
    await db.commit()
    await cache.remember_post(post.id)
    return PostResponse.model_validate(post)


@router.get("/", response_model=list[PostResponse])
async def get_posts(
    db: SessionDB,
    after_id: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    posts = await db.scalars(
        select(Post).where(Post.id > after_id).order_by(Post.id).limit(limit)
    )
    return posts.all()


@router.get("/{post_id}", response_model=PostDetailResponse)
async def get_post(post_id: int, db: SessionDB, request: Request):
    cache: CounterCache = request.app.state.counter_cache
    cached = await cache.get(post_id)
    if cached is not None:
        return cached
    read_started = time.monotonic()
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(404, "Post not found")
    counts = (await db.execute(
        select(
            func.coalesce(func.sum(PostCounter.likes_count), 0),
            func.coalesce(func.sum(PostCounter.views_count), 0),
        ).where(PostCounter.post_id == post_id)
    )).one()
    response = {
        "post_id": post.id, "content": post.content,
        "likes_count": int(counts[0]), "views_count": int(counts[1]),
    }
    await cache.put(post_id, response, read_started)
    return response

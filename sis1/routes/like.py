from fastapi import APIRouter, status

from database.session import SessionDB
from routes.engagement import accept_event
from schemas.like import LikeRequest, LikeResponse
from services.cache import CacheDep
from services.publisher import PublisherDep

router = APIRouter(prefix="/like", tags=["Like"])


@router.post("", response_model=LikeResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_like(obj_in: LikeRequest, db: SessionDB, publisher: PublisherDep, cache: CacheDep):
    return await accept_event("like", obj_in, db, publisher, cache)

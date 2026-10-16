from fastapi import APIRouter, status

from database.session import SessionDB
from routes.engagement import accept_event
from schemas.view import ViewRequest, ViewResponse
from services.cache import CacheDep
from services.publisher import PublisherDep

router = APIRouter(prefix="/view", tags=["View"])


@router.post("", response_model=ViewResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_view(obj_in: ViewRequest, db: SessionDB, publisher: PublisherDep, cache: CacheDep):
    return await accept_event("view", obj_in, db, publisher, cache)

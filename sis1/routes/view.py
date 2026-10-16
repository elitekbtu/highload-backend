from fastapi import APIRouter, HTTPException
from schemas.view import ViewRequest, ViewResponse


from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND


from database.session import SessionDB
from models import View
from models import Post

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

    data = obj_in.model_dump()
    view = View(**data)
    db.add(view)
    db.commit()
    db.refresh(view)
    response = ViewResponse.model_validate(view)
    return response

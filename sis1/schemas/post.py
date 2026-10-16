from pydantic import BaseModel, ConfigDict


class PostRequest(BaseModel):
    content: str | None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content: str | None


class PostDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: int
    content: str | None

    likes_count: int
    views_count: int

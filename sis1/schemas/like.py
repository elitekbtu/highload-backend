from pydantic import BaseModel, ConfigDict


class LikeRequest(BaseModel):
    username: str
    post_id: int


class LikeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_id: int

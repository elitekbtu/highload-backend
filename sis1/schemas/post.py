from pydantic import BaseModel, ConfigDict


class PostRequest(BaseModel):
    content: str


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content: str

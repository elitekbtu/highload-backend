from pydantic import BaseModel


class PostRequest(BaseModel):
    content: str


class PostResponse(BaseModel):
    id: int
    content: str

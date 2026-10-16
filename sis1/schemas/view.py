from pydantic import BaseModel, ConfigDict


class ViewRequest(BaseModel):
    post_id: int


class ViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_id: int

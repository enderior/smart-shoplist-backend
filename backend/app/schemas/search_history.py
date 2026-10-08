from pydantic import BaseModel, Field
from datetime import datetime


class SearchHistoryResponse(BaseModel):
    id: int
    query: str
    list_id: int | None = None
    searched_at: datetime

    class Config:
        from_attributes = True


class SearchHistoryCreate(BaseModel):
    query: str = Field(min_length=1, max_length=255)
    list_id: int | None = None

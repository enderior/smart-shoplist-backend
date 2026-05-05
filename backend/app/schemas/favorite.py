from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.shopping_list import ListItemResponse


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    created_at: datetime
    item: Optional[ListItemResponse] = None

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    item_id: int

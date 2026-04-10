from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ListItemBase(BaseModel):
    name: str
    quantity: int = 1
    unit: Optional[str] = None
    is_completed: bool = False
    position: int = 0

class ListItemCreate(ListItemBase):
    pass

class ListItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    is_completed: Optional[bool] = None
    position: Optional[int] = None

class ListItemResponse(ListItemBase):
    id: int
    list_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ShoppingListBase(BaseModel):
    title: str
    description: Optional[str] = None

class ShoppingListCreate(ShoppingListBase):
    pass

class ShoppingListUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None

class ShoppingListResponse(ShoppingListBase):
    id: int
    owner_id: int
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: Optional[List[ListItemResponse]] = None
    
    class Config:
        from_attributes = True

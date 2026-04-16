from pydantic import BaseModel
from datetime import datetime

class PurchaseHistoryResponse(BaseModel):
    id: int
    product_name: str
    purchased_at: datetime

    class Config:
        from_attributes = True
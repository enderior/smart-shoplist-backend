from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.purchase_history import PurchaseHistory
from app.schemas.purchase_history import PurchaseHistoryResponse

router = APIRouter(prefix="/purchase-history", tags=["Purchase History"])

@router.get("/", response_model=list[PurchaseHistoryResponse])
async def get_purchase_history(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(PurchaseHistory)
        .where(PurchaseHistory.user_id == current_user.id)
        .order_by(PurchaseHistory.purchased_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
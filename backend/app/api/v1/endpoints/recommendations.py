from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.purchase_history import PurchaseHistory

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Статический словарь ассоциаций (можно расширять)
STATIC_ASSOCIATIONS = {
    "хлеб": ["масло", "молоко", "колбаса"],
    "молоко": ["хлеб", "печенье", "масло"],
    "пиво": ["чипсы", "сухарики", "орешки"],
    "яйца": ["масло", "молоко", "хлеб"],
    "колбаса": ["хлеб", "масло", "сыр"],
    "сыр": ["хлеб", "масло", "вино"],
}

@router.get("/{product_name}")
async def get_recommendations(
    product_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    product_lower = product_name.lower()

    # 1. Статические рекомендации из словаря
    static_recs = STATIC_ASSOCIATIONS.get(product_lower, [])

    # 2. Динамические рекомендации на основе истории покупок пользователя
    # Находим даты, когда пользователь покупал указанный товар
    date_subq = (
        select(PurchaseHistory.purchased_at)
        .where(
            PurchaseHistory.user_id == current_user.id,
            PurchaseHistory.product_name == product_lower
        )
        .subquery()
    )

    # Выбираем другие товары, купленные в те же даты
    result = await db.execute(
        select(PurchaseHistory.product_name, func.count().label("cnt"))
        .where(
            PurchaseHistory.user_id == current_user.id,
            PurchaseHistory.purchased_at.in_(select(date_subq.c.purchased_at)),
            PurchaseHistory.product_name != product_lower
        )
        .group_by(PurchaseHistory.product_name)
        .order_by(func.count().desc())
        .limit(5)
    )
    dynamic_recs = [row[0] for row in result.all()]

    # Объединяем, убирая дубликаты
    all_recs = list(dict.fromkeys(static_recs + dynamic_recs))

    return {"recommendations": all_recs}
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ListItem
from app.models.purchase_history import PurchaseHistory

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/suggestions")
async def get_suggestions(
        q: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        limit: int = 5
):
    if not q or len(q.strip()) < 2:
        return {"suggestions": [], "query": q}

    query_lower = q.strip().lower()
    suggestions_set = set()

    # 1. Поиск в списках товаров (просто выбираем все названия и фильтруем в Python)
    lists_result = await db.execute(
        select(ListItem.name).distinct()
    )
    for row in lists_result:
        name = row[0]
        if query_lower in name.lower():
            suggestions_set.add(name)
            if len(suggestions_set) >= limit:
                break

    # 2. Поиск в истории покупок пользователя
    if len(suggestions_set) < limit:
        history_result = await db.execute(
            select(PurchaseHistory.product_name)
            .where(PurchaseHistory.user_id == current_user.id)
            .distinct()
        )
        for row in history_result:
            name = row[0]
            if query_lower in name.lower():
                suggestions_set.add(name)
                if len(suggestions_set) >= limit:
                    break

    # 3. Если мало результатов – добавим популярные товары (из истории всех пользователей)
    if len(suggestions_set) < limit:
        popular_result = await db.execute(
            select(PurchaseHistory.product_name)
            .distinct()
        )
        for row in popular_result:
            name = row[0]
            if query_lower in name.lower() and name not in suggestions_set:
                suggestions_set.add(name)
                if len(suggestions_set) >= limit:
                    break

    suggestions = list(suggestions_set)[:limit]
    return {"suggestions": suggestions, "query": q}

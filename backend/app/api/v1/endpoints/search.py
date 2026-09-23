from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem
from app.models.search_history import SearchHistory
from app.models.product import Product

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/suggestions")
async def get_suggestions(
        q: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        limit: int = 5
):
    """
    Подсказки для автодополнения:
    1) товары из личных списков пользователя,
    2) личная история поиска,
    3) глобальная база товаров (если своих результатов мало).

    Фильтрация выполняется в Python, потому что SQLite не поддерживает
    регистронезависимый поиск для кириллицы (LOWER/ILIKE не работают).
    """
    if not q or len(q.strip()) < 2:
        return {"suggestions": [], "query": q}

    query_lower = q.strip().lower()
    suggestions_set = set()

    # 1. Товары из личных списков пользователя
    lists_result = await db.execute(
        select(ListItem.name)
        .join(ShoppingList, ShoppingList.id == ListItem.list_id)
        .where(ShoppingList.owner_id == current_user.id)
        .distinct()
    )
    for row in lists_result:
        name = row[0]
        if query_lower in name.lower():
            suggestions_set.add(name)
            if len(suggestions_set) >= limit:
                break

    # 2. Личная история поиска
    if len(suggestions_set) < limit:
        history_result = await db.execute(
            select(SearchHistory.product_name)
            .where(SearchHistory.user_id == current_user.id)
            .distinct()
        )
        for row in history_result:
            name = row[0]
            if query_lower in name.lower():
                suggestions_set.add(name)
                if len(suggestions_set) >= limit:
                    break

    # 3. Глобальная база товаров
    if len(suggestions_set) < limit:
        products_result = await db.execute(
            select(Product.name).distinct()
        )
        for row in products_result:
            name = row[0]
            if query_lower in name.lower() and name not in suggestions_set:
                suggestions_set.add(name)
                if len(suggestions_set) >= limit:
                    break

    return {"suggestions": list(suggestions_set)[:limit], "query": q}

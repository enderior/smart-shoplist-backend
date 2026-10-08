from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem
from app.models.search_history import SearchHistory
from app.models.product import Product
from app.schemas.search_history import SearchHistoryResponse, SearchHistoryCreate

router = APIRouter(prefix="/search", tags=["Search"])


def _to_response(entry: SearchHistory) -> SearchHistoryResponse:
    return SearchHistoryResponse(
        id=entry.id,
        query=entry.product_name,
        list_id=None,
        searched_at=entry.created_at,
    )


async def _find_history_entry(db: AsyncSession, user_id: int, normalized: str):
    # Регистронезависимый поиск выполняется в Python: SQLite не понимает
    # LOWER() для кириллицы (см. хелперы в endpoints/lists.py).
    result = await db.execute(
        select(SearchHistory).where(SearchHistory.user_id == user_id)
    )
    return next(
        (h for h in result.scalars().all()
         if h.product_name.strip().lower() == normalized),
        None,
    )


@router.get("/history", response_model=list[SearchHistoryResponse])
async def get_search_history(
        limit: int = 20,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(max(limit, 0))
    )
    return [_to_response(entry) for entry in result.scalars().all()]


@router.post("/history", response_model=SearchHistoryResponse)
async def save_search_history(
        entry: SearchHistoryCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    query = entry.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Поисковый запрос не может быть пустым",
        )

    normalized = query.lower()
    history = await _find_history_entry(db, current_user.id, normalized)
    if history:
        history.product_name = query
        history.created_at = datetime.now(timezone.utc)
    else:
        history = SearchHistory(user_id=current_user.id, product_name=query)
        db.add(history)

    await db.commit()
    await db.refresh(history)
    return _to_response(history)


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

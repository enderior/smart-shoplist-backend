from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem
from app.models.list_member import ListMember
from app.models.purchase_history import PurchaseHistory
from app.data.associations import STATIC_ASSOCIATIONS

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Окно, в пределах которого покупки считаются «одним походом в магазин»
PURCHASE_WINDOW = timedelta(hours=3)


def _to_utc(dt):
    """Приводит naive datetime к aware UTC. Нужно для сравнения на SQLite."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/list/{list_id}")
async def get_recommendations_for_list(
        list_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Возвращает рекомендации для указанного списка.
    Доступен владельцу и участникам (read/write).
    Объединяет статические ассоциации и историю покупок.
    """
    # 1. Проверяем доступ к списку
    result = await db.execute(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    if shopping_list.owner_id != current_user.id:
        member = await db.execute(
            select(ListMember).where(
                ListMember.list_id == list_id,
                ListMember.user_id == current_user.id
            )
        )
        if not member.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="List not found")

    # 2. Товары из списка (нормализуем)
    items_result = await db.execute(
        select(ListItem.name).where(ListItem.list_id == list_id)
    )
    existing_items = {row[0].strip().lower() for row in items_result.all()}

    if not existing_items:
        return {"recommendations": [], "list_id": list_id}

    # 3. Статические рекомендации
    static_scores = {}
    for item_lower in existing_items:
        if item_lower in STATIC_ASSOCIATIONS:
            for confidence, product in STATIC_ASSOCIATIONS[item_lower]:
                product_lower = product.strip().lower()
                if product_lower not in existing_items:
                    static_scores[product_lower] = (
                        static_scores.get(product_lower, 0) + confidence
                    )

    # 4. Динамические рекомендации из истории покупок (Python-side,
    #    чтобы не зависеть от LOWER() в SQLite для кириллицы).
    history_result = await db.execute(
        select(PurchaseHistory.product_name, PurchaseHistory.purchased_at)
        .where(PurchaseHistory.user_id == current_user.id)
    )
    history = [
        (name.strip().lower(), _to_utc(dt))
        for name, dt in history_result.all()
    ]

    dynamic_scores = {}
    for item_lower in existing_items:
        # Все даты покупки текущего товара
        item_dates = [dt for name, dt in history if name == item_lower and dt]
        if not item_dates:
            continue

        # Считаем, сколько раз другие товары покупались «вместе» с ним
        counts = {}
        for other_name, other_dt in history:
            if other_name == item_lower or other_dt is None:
                continue
            for item_dt in item_dates:
                if abs(other_dt - item_dt) <= PURCHASE_WINDOW:
                    counts[other_name] = counts.get(other_name, 0) + 1
                    break  # не считаем один и тот же other много раз

        if not counts:
            continue

        max_cnt = max(counts.values())
        for product_lower, cnt in counts.items():
            if product_lower not in existing_items:
                confidence = cnt / max_cnt
                dynamic_scores[product_lower] = (
                    dynamic_scores.get(product_lower, 0) + confidence
                )

    # 5. Объединяем: динамика с весом 0.7
    final_scores = {}
    for product, score in static_scores.items():
        final_scores[product] = score
    for product, score in dynamic_scores.items():
        final_scores[product] = final_scores.get(product, 0) + score * 0.7

    # 6. Топ-5
    sorted_products = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top_5 = [product for product, _ in sorted_products[:5]]

    return {"recommendations": top_5, "list_id": list_id}
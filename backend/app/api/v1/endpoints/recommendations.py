from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem
from app.models.list_member import ListMember
from app.models.purchase_history import PurchaseHistory
from app.data.associations import STATIC_ASSOCIATIONS

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/list/{list_id}")
async def get_recommendations_for_list(
        list_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Возвращает рекомендации для указанного списка.
    Доступен владельцу и участникам (read/write).
    """
    # 1. Проверяем список (владелец или участник)
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

    # 2. Товары из списка (lowercase)
    items_result = await db.execute(
        select(ListItem.name).where(ListItem.list_id == list_id)
    )
    existing_items = {row[0].strip().lower() for row in items_result.all()}

    if not existing_items:
        return {"recommendations": [], "list_id": list_id}

    # 3. Статические рекомендации
    static_scores = {}
    for item_name in existing_items:
        if item_name in STATIC_ASSOCIATIONS:
            for confidence, product in STATIC_ASSOCIATIONS[item_name]:
                product_lower = product.strip().lower()
                if product_lower not in existing_items:
                    static_scores[product] = static_scores.get(product, 0) + confidence

    # 4. Динамические рекомендации из истории (case-insensitive)
    dynamic_scores = {}
    for item_name in existing_items:
        item_lower = item_name.lower()

        date_subq = (
            select(PurchaseHistory.purchased_at)
            .where(
                PurchaseHistory.user_id == current_user.id,
                func.lower(PurchaseHistory.product_name) == item_lower  # ← ФИКС #1
            )
            .subquery()
        )

        hist_result = await db.execute(
            select(PurchaseHistory.product_name, func.count().label("cnt"))
            .where(
                PurchaseHistory.user_id == current_user.id,
                PurchaseHistory.purchased_at.in_(select(date_subq.c.purchased_at)),
                func.lower(PurchaseHistory.product_name) != item_lower  # ← ФИКС #1
            )
            .group_by(PurchaseHistory.product_name)
            .order_by(func.count().desc())
            .limit(10)
        )

        rows = hist_result.all()
        if rows:
            max_cnt = max(row[1] for row in rows)
            for product, cnt in rows:
                product_lower = product.strip().lower()
                if product_lower not in existing_items:
                    confidence = cnt / max_cnt if max_cnt > 0 else 0
                    dynamic_scores[product] = dynamic_scores.get(product, 0) + confidence

    # 5. Объединяем
    final_scores = {}
    for product, score in static_scores.items():
        final_scores[product] = score
    for product, score in dynamic_scores.items():
        final_scores[product] = final_scores.get(product, 0) + score * 0.7

    sorted_products = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top_5_products = [product for product, _ in sorted_products[:5]]

    return {"recommendations": top_5_products, "list_id": list_id}

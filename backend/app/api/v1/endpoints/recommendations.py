from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem
from app.models.purchase_history import PurchaseHistory

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Статические ассоциации: ключ — товар, значение — список [коэффициент, рекомендуемый товар]
STATIC_ASSOCIATIONS = {
    "хлеб": [
        [0.92, "масло"],
        [0.88, "колбаса"],
        [0.84, "сыр"],
        [0.78, "молоко"],
        [0.70, "яйца"],
        [0.65, "сметана"],
        [0.60, "курица"],
        [0.55, "помидоры"],
        [0.50, "огурцы"]
    ],
    "молоко": [
        [0.88, "хлеб"],
        [0.82, "масло"],
        [0.78, "творог"],
        [0.74, "яйца"],
        [0.68, "сыр"],
        [0.62, "рис"],
        [0.55, "сметана"],
        [0.50, "курица"]
    ],
    "масло": [
        [0.92, "хлеб"],
        [0.84, "молоко"],
        [0.78, "яйца"],
        [0.74, "сыр"],
        [0.68, "колбаса"],
        [0.62, "картофель"],
        [0.55, "курица"],
        [0.50, "мука"]
    ],
    "яйца": [
        [0.86, "масло"],
        [0.82, "молоко"],
        [0.76, "хлеб"],
        [0.72, "сметана"],
        [0.66, "сыр"],
        [0.60, "колбаса"],
        [0.55, "курица"],
        [0.50, "мука"]
    ],
    "колбаса": [
        [0.92, "хлеб"],
        [0.80, "сыр"],
        [0.76, "масло"],
        [0.70, "яйца"],
        [0.64, "курица"],
        [0.58, "макароны"],
        [0.52, "картофель"],
        [0.48, "кетчуп"]
    ],
    "сыр": [
        [0.90, "хлеб"],
        [0.82, "масло"],
        [0.78, "макароны"],
        [0.74, "колбаса"],
        [0.68, "яйца"],
        [0.62, "курица"],
        [0.56, "сметана"],
        [0.50, "помидоры"]
    ],
    "курица": [
        [0.86, "картофель"],
        [0.80, "рис"],
        [0.76, "масло"],
        [0.70, "сметана"],
        [0.64, "яйца"],
        [0.58, "хлеб"],
        [0.52, "помидоры"],
        [0.48, "макароны"]
    ],
    "картофель": [
        [0.88, "курица"],
        [0.82, "масло"],
        [0.78, "сметана"],
        [0.72, "яйца"],
        [0.66, "молоко"],
        [0.60, "сыр"],
        [0.54, "колбаса"],
        [0.48, "лук"]
    ],
    "рис": [
        [0.88, "курица"],
        [0.82, "масло"],
        [0.78, "яйца"],
        [0.72, "молоко"],
        [0.66, "сметана"],
        [0.60, "сыр"],
        [0.54, "колбаса"],
        [0.48, "помидоры"]
    ],
    "макароны": [
        [0.90, "сыр"],
        [0.84, "курица"],
        [0.78, "масло"],
        [0.72, "сметана"],
        [0.66, "колбаса"],
        [0.60, "яйца"],
        [0.54, "молоко"],
        [0.48, "кетчуп"]
    ],
    "сметана": [
        [0.92, "творог"],
        [0.80, "картофель"],
        [0.76, "яйца"],
        [0.70, "курица"],
        [0.64, "масло"],
        [0.58, "хлеб"],
        [0.52, "сыр"],
        [0.46, "рис"]
    ],
    "творог": [
        [0.92, "сметана"],
        [0.82, "яйца"],
        [0.78, "молоко"],
        [0.72, "масло"],
        [0.66, "хлеб"],
        [0.60, "сыр"],
        [0.54, "рис"],
        [0.48, "сахар"]
    ],
    "помидоры": [
        [0.84, "огурцы"],
        [0.78, "хлеб"],
        [0.72, "курица"],
        [0.66, "сыр"],
        [0.60, "масло"],
        [0.54, "лук"],
        [0.48, "сметана"],
        [0.42, "макароны"]
    ],
    "огурцы": [
        [0.84, "помидоры"],
        [0.78, "хлеб"],
        [0.72, "курица"],
        [0.66, "сметана"],
        [0.60, "масло"],
        [0.54, "лук"],
        [0.48, "сыр"],
        [0.42, "яйца"]
    ],
    "чай": [
        [0.88, "сахар"],
        [0.74, "хлеб"],
        [0.68, "молоко"],
        [0.62, "масло"],
        [0.56, "печенье"],
        [0.50, "лимон"],
        [0.44, "конфеты"],
        [0.38, "мёд"]
    ],
    "кофе": [
        [0.86, "сахар"],
        [0.78, "молоко"],
        [0.72, "хлеб"],
        [0.66, "сливки"],
        [0.60, "печенье"],
        [0.54, "масло"],
        [0.48, "конфеты"],
        [0.42, "шоколад"]
    ],
    "сахар": [
        [0.90, "чай"],
        [0.80, "кофе"],
        [0.72, "мука"],
        [0.64, "яйца"],
        [0.56, "масло"],
        [0.48, "молоко"],
        [0.40, "творог"],
        [0.34, "печенье"]
    ],
    "мука": [
        [0.84, "яйца"],
        [0.78, "сахар"],
        [0.72, "масло"],
        [0.66, "молоко"],
        [0.60, "сметана"],
        [0.54, "дрожжи"],
        [0.48, "разрыхлитель"],
        [0.42, "хлеб"]
    ],
    "кетчуп": [
        [0.82, "макароны"],
        [0.76, "колбаса"],
        [0.70, "курица"],
        [0.64, "картофель"],
        [0.58, "хлеб"],
        [0.52, "сосиски"],
        [0.46, "сыр"],
        [0.40, "майонез"]
    ]
}


@router.get("/list/{list_id}")
async def get_recommendations_for_list(
        list_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Возвращает рекомендации для указанного списка.
    - Объединяет статические ассоциации и историю покупок.
    - Суммирует коэффициенты.
    - Исключает товары, которые уже есть в списке.
    - Возвращает топ-5 рекомендуемых товаров.
    """
    # 1. Проверяем список и права доступа
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    # 2. Получаем все товары, которые уже есть в списке
    items_result = await db.execute(
        select(ListItem.name).where(ListItem.list_id == list_id)
    )
    existing_items = {row[0].lower() for row in items_result.all()}
    list_items = [row[0] for row in items_result.all()]

    # 3. Статические рекомендации
    static_scores = {}
    for item_name in list_items:
        item_lower = item_name.lower()
        if item_lower in STATIC_ASSOCIATIONS:
            for confidence, product in STATIC_ASSOCIATIONS[item_lower]:
                product_lower = product.lower()
                if product_lower not in existing_items:
                    static_scores[product] = static_scores.get(product, 0) + confidence

    # 4. Динамические рекомендации из истории покупок
    dynamic_scores = {}
    for item_name in list_items:
        item_lower = item_name.lower()

        date_subq = (
            select(PurchaseHistory.purchased_at)
            .where(
                PurchaseHistory.user_id == current_user.id,
                PurchaseHistory.product_name == item_lower
            )
            .subquery()
        )

        hist_result = await db.execute(
            select(PurchaseHistory.product_name, func.count().label("cnt"))
            .where(
                PurchaseHistory.user_id == current_user.id,
                PurchaseHistory.purchased_at.in_(select(date_subq.c.purchased_at)),
                PurchaseHistory.product_name != item_lower
            )
            .group_by(PurchaseHistory.product_name)
            .order_by(func.count().desc())
            .limit(10)
        )

        rows = hist_result.all()
        if rows:
            max_cnt = max(row[1] for row in rows)
            for product, cnt in rows:
                product_lower = product.lower()
                if product_lower not in existing_items:
                    confidence = cnt / max_cnt if max_cnt > 0 else 0
                    dynamic_scores[product] = dynamic_scores.get(product, 0) + confidence

    # 5. Объединяем (динамика с весом 0.7)
    final_scores = {}
    for product, score in static_scores.items():
        final_scores[product] = score
    for product, score in dynamic_scores.items():
        final_scores[product] = final_scores.get(product, 0) + score * 0.7

    # 6. Исключаем уже существующие товары
    for product in list(existing_items):
        final_scores.pop(product, None)

    # 7. Сортируем и берём топ-5
    sorted_products = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top_5_products = [product for product, _ in sorted_products[:5]]

    return {"recommendations": top_5_products, "list_id": list_id}
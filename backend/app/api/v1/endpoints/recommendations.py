from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Статические ассоциации: ключ — товар, значение — список [коэффициент, рекомендуемый товар]
STATIC_ASSOCIATIONS = {
    "хлеб": [
        [0.95, "масло"],
        [0.90, "колбаса"],
        [0.85, "сыр"],
        [0.80, "молоко"],
        [0.70, "яйца"],
        [0.65, "мясо"],
        [0.60, "сметана"]
    ],
    "молоко": [
        [0.90, "хлеб"],
        [0.85, "масло"],
        [0.80, "творог"],
        [0.75, "яйца"],
        [0.70, "сыр"],
        [0.65, "рис"],
        [0.60, "сметана"]
    ],
    "масло": [
        [0.95, "хлеб"],
        [0.85, "молоко"],
        [0.80, "яйца"],
        [0.75, "сыр"],
        [0.70, "колбаса"],
        [0.65, "картофель"],
        [0.60, "мясо"]
    ],
    "яйца": [
        [0.90, "масло"],
        [0.85, "молоко"],
        [0.80, "хлеб"],
        [0.75, "сметана"],
        [0.70, "сыр"],
        [0.65, "колбаса"],
        [0.60, "мясо"]
    ],
    "колбаса": [
        [0.95, "хлеб"],
        [0.85, "масло"],
        [0.80, "сыр"],
        [0.75, "яйца"],
        [0.70, "мясо"],
        [0.65, "картофель"],
        [0.60, "макароны"]
    ],
    "сыр": [
        [0.95, "хлеб"],
        [0.85, "масло"],
        [0.80, "колбаса"],
        [0.75, "макароны"],
        [0.70, "яйца"],
        [0.65, "мясо"],
        [0.60, "сметана"]
    ],
    "мясо": [
        [0.95, "картофель"],
        [0.85, "масло"],
        [0.80, "сметана"],
        [0.75, "рис"],
        [0.70, "макароны"],
        [0.65, "яйца"],
        [0.60, "хлеб"]
    ],
    "картофель": [
        [0.95, "мясо"],
        [0.85, "масло"],
        [0.80, "сметана"],
        [0.75, "молоко"],
        [0.70, "яйца"],
        [0.65, "сыр"],
        [0.60, "колбаса"]
    ],
    "рис": [
        [0.95, "мясо"],
        [0.85, "масло"],
        [0.80, "яйца"],
        [0.75, "молоко"],
        [0.70, "сметана"],
        [0.65, "сыр"],
        [0.60, "колбаса"]
    ],
    "макароны": [
        [0.95, "сыр"],
        [0.90, "мясо"],
        [0.85, "масло"],
        [0.80, "сметана"],
        [0.75, "колбаса"],
        [0.70, "яйца"],
        [0.65, "молоко"]
    ],
    "сметана": [
        [0.95, "творог"],
        [0.85, "картофель"],
        [0.80, "яйца"],
        [0.75, "мясо"],
        [0.70, "масло"],
        [0.65, "хлеб"],
        [0.60, "сыр"]
    ],
    "творог": [
        [0.95, "сметана"],
        [0.85, "яйца"],
        [0.80, "молоко"],
        [0.75, "масло"],
        [0.70, "хлеб"],
        [0.65, "сыр"],
        [0.60, "рис"]
    ]
}

@router.get("/list/{list_id}")
async def get_recommendations_for_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Возвращает рекомендации для указанного списка на основе статических ассоциаций.
    - Исключает товары, которые уже есть в списке.
    - Суммирует коэффициенты из статического словаря.
    - Сортирует по убыванию суммарного коэффициента.
    - Возвращает топ-5 рекомендуемых товаров.
    """
    # 1. Проверяем, существует ли список и принадлежит ли он пользователю
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

    # 3. Собираем статические рекомендации (суммируем коэффициенты)
    scores = {}
    for item_name in existing_items:
        if item_name in STATIC_ASSOCIATIONS:
            for confidence, product in STATIC_ASSOCIATIONS[item_name]:
                product_lower = product.lower()
                if product_lower not in existing_items:
                    scores[product] = scores.get(product, 0) + confidence

    # 4. Сортируем по убыванию суммарного коэффициента
    sorted_products = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # 5. Возвращаем топ-5 названий товаров (без коэффициентов)
    top_5_products = [product for product, _ in sorted_products[:5]]

    return {"recommendations": top_5_products, "list_id": list_id}
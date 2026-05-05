from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ListItem
from app.models.favorite import FavoriteItem
from app.schemas.favorite import FavoriteResponse

router = APIRouter(prefix="/favorites", tags=["Favorites"])


# ========== ДОБАВИТЬ В ИЗБРАННОЕ ==========
@router.post("/{item_id}", status_code=status.HTTP_201_CREATED)
async def add_to_favorites(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Добавляет товар в избранное."""

    # Проверяем, существует ли товар
    item_result = await db.execute(select(ListItem).where(ListItem.id == item_id))
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверяем, не добавлен ли уже в избранное
    existing = await db.execute(
        select(FavoriteItem).where(
            FavoriteItem.user_id == current_user.id,
            FavoriteItem.item_id == item_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Товар уже в избранном")

    favorite = FavoriteItem(user_id=current_user.id, item_id=item_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    return {"message": "Товар добавлен в избранное", "favorite_id": favorite.id}


# ========== УДАЛИТЬ ИЗ ИЗБРАННОГО ==========
@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Удаляет товар из избранного."""

    result = await db.execute(
        delete(FavoriteItem).where(
            FavoriteItem.user_id == current_user.id,
            FavoriteItem.item_id == item_id
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Товар не найден в избранном")

    await db.commit()


# ========== СПИСОК ИЗБРАННЫХ ТОВАРОВ ==========
@router.get("/", response_model=list[FavoriteResponse])
async def get_favorites(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        skip: int = 0,
        limit: int = 50
):
    """Возвращает список избранных товаров текущего пользователя."""

    result = await db.execute(
        select(FavoriteItem)
        .where(FavoriteItem.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .order_by(FavoriteItem.created_at.desc())
    )
    favorites = result.scalars().all()

    # Подгружаем информацию о товарах
    for fav in favorites:
        item_result = await db.execute(select(ListItem).where(ListItem.id == fav.item_id))
        fav.item = item_result.scalar_one_or_none()

    return favorites

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem
from app.models.purchase_history import PurchaseHistory
from app.schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingListResponse,
    ListItemCreate,
    ListItemUpdate,
    ListItemResponse
)

router = APIRouter(prefix="/lists", tags=["Shopping Lists"])


# ========== ЭНДПОИНТЫ ДЛЯ СПИСКОВ ==========

@router.post("/", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
        list_data: ShoppingListCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Создаёт новый список покупок для текущего пользователя."""
    new_list = ShoppingList(
        title=list_data.title,
        description=list_data.description,
        owner_id=current_user.id
    )
    db.add(new_list)
    await db.commit()
    await db.refresh(new_list)

    return ShoppingListResponse(
        id=new_list.id,
        title=new_list.title,
        description=new_list.description,
        owner_id=new_list.owner_id,
        is_archived=new_list.is_archived,
        created_at=new_list.created_at,
        updated_at=new_list.updated_at,
        items=[]
    )


@router.get("/", response_model=list[ShoppingListResponse])
async def get_user_lists(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Возвращает ВСЕ списки текущего пользователя (без товаров)."""
    result = await db.execute(
        select(ShoppingList).where(ShoppingList.owner_id == current_user.id)
    )
    lists = result.scalars().all()

    return [
        ShoppingListResponse(
            id=item.id,
            title=item.title,
            description=item.description,
            owner_id=item.owner_id,
            is_archived=item.is_archived,
            created_at=item.created_at,
            updated_at=item.updated_at,
            items=[]
        )
        for item in lists
    ]


@router.get("/{list_id}", response_model=ShoppingListResponse)
async def get_list_by_id(
        list_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Возвращает один список по ID с его товарами."""
    result = await db.execute(
        select(ShoppingList)
        .where(ShoppingList.id == list_id, ShoppingList.owner_id == current_user.id)
        .options(selectinload(ShoppingList.items))
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")
    return shopping_list


@router.put("/{list_id}", response_model=ShoppingListResponse)
async def update_list(
        list_id: int,
        list_data: ShoppingListUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Обновляет название или описание списка."""
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    shopping_list = result.scalar_one_or_none()

    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    if list_data.title is not None:
        shopping_list.title = list_data.title
    if list_data.description is not None:
        shopping_list.description = list_data.description
    if list_data.is_archived is not None:
        shopping_list.is_archived = list_data.is_archived

    await db.commit()
    await db.refresh(shopping_list)

    # Подгружаем товары для ответа
    result = await db.execute(
        select(ShoppingList)
        .where(ShoppingList.id == list_id)
        .options(selectinload(ShoppingList.items))
    )
    updated_list = result.scalar_one()

    return updated_list


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
        list_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Удаляет список покупок (вместе со всеми товарами)."""
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    shopping_list = result.scalar_one_or_none()

    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    await db.delete(shopping_list)
    await db.commit()


# ========== ЭНДПОИНТЫ ДЛЯ ТОВАРОВ ==========

@router.post("/{list_id}/items", response_model=ListItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_list(
        list_id: int,
        item_data: ListItemCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Добавляет новый товар в указанный список."""
    # Проверяем, существует ли список и принадлежит ли он пользователю
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    shopping_list = result.scalar_one_or_none()

    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    # Создаём новый товар
    new_item = ListItem(
        list_id=list_id,
        name=item_data.name,
        quantity=item_data.quantity,
        unit=item_data.unit,
        position=item_data.position
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    return new_item


@router.put("/items/{item_id}", response_model=ListItemResponse)
async def update_item(
        item_id: int,
        item_data: ListItemUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    # Находим товар и проверяем, что он принадлежит пользователю
    result = await db.execute(
        select(ListItem)
        .join(ShoppingList)
        .where(
            ListItem.id == item_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Сохраняем старое значение is_completed ДО обновления
    old_completed = item.is_completed

    # Обновляем поля
    if item_data.name is not None:
        item.name = item_data.name
    if item_data.quantity is not None:
        item.quantity = item_data.quantity
    if item_data.unit is not None:
        item.unit = item_data.unit
    if item_data.position is not None:
        item.position = item_data.position
    if item_data.is_completed is not None:
        item.is_completed = item_data.is_completed

    # Если статус изменился с False на True – добавляем в историю
    if not old_completed and item.is_completed is True:
        history_entry = PurchaseHistory(
            user_id=current_user.id,
            product_name=item.name
        )
        db.add(history_entry)

    await db.commit()
    await db.refresh(item)

    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Удаляет товар из списка."""
    # Находим товар и проверяем, что он принадлежит пользователю через список
    result = await db.execute(
        select(ListItem)
        .join(ShoppingList)
        .where(
            ListItem.id == item_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await db.commit()
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList, ListItem
from app.models.purchase_history import PurchaseHistory
from app.models.list_member import ListMember  # Добавлен импорт
from app.schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingListResponse,
    ListItemCreate,
    ListItemUpdate,
    ListItemResponse
)

router = APIRouter(prefix="/lists", tags=["Shopping Lists"])


@router.post("/", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
        list_data: ShoppingListCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Создаёт новый список покупок для текущего пользователя."""
    new_list = ShoppingList(
        title=list_data.title,
        owner_id=current_user.id
    )
    db.add(new_list)
    await db.commit()
    await db.refresh(new_list)

    return ShoppingListResponse(
        id=new_list.id,
        title=new_list.title,
        owner_id=new_list.owner_id,
        created_at=new_list.created_at,
        updated_at=new_list.updated_at,
        items=[]
    )


@router.get("/", response_model=list[ShoppingListResponse])
async def get_user_lists(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Возвращает ВСЕ списки, доступные пользователю (свои + совместные)."""
    own_result = await db.execute(
        select(ShoppingList).where(ShoppingList.owner_id == current_user.id)
    )
    own_lists = own_result.scalars().all()

    shared_result = await db.execute(
        select(ShoppingList)
        .join(ListMember, ListMember.list_id == ShoppingList.id)
        .where(ListMember.user_id == current_user.id)
    )
    shared_lists = shared_result.scalars().all()

    all_lists_dict = {}
    for lst in own_lists:
        all_lists_dict[lst.id] = lst
    for lst in shared_lists:
        if lst.id not in all_lists_dict:
            all_lists_dict[lst.id] = lst

    return [
        ShoppingListResponse(
            id=item.id,
            title=item.title,
            owner_id=item.owner_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
            items=[]
        )
        for item in all_lists_dict.values()
    ]


@router.get("/{list_id}", response_model=ShoppingListResponse)
async def get_list_by_id(
        list_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Возвращает один список по ID с его товарами."""
    # Проверяем доступ: владелец или участник (read/write)
    result = await db.execute(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    is_owner = shopping_list.owner_id == current_user.id
    if not is_owner:
        member = await db.execute(
            select(ListMember).where(
                ListMember.list_id == list_id,
                ListMember.user_id == current_user.id
            )
        )
        if not member.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="List not found or no access")

    # Подгружаем товары
    result = await db.execute(
        select(ShoppingList)
        .where(ShoppingList.id == list_id)
        .options(selectinload(ShoppingList.items))
    )
    shopping_list = result.scalar_one()
    return shopping_list


async def check_write_permission(list_id: int, user_id: int, db: AsyncSession) -> bool:
    """Проверяет, имеет ли пользователь право write для списка."""
    # Проверяем владельца
    list_result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == user_id
        )
    )
    if list_result.scalar_one_or_none():
        return True

    # Проверяем участника с правом write
    member = await db.execute(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == user_id,
            ListMember.permission == "write"
        )
    )
    return member.scalar_one_or_none() is not None


@router.put("/{list_id}", response_model=ShoppingListResponse)
async def update_list(
        list_id: int,
        list_data: ShoppingListUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Обновляет название списка. Требует права write."""
    if not await check_write_permission(list_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    result = await db.execute(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    if list_data.title is not None:
        shopping_list.title = list_data.title

    await db.commit()
    await db.refresh(shopping_list)

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
    """Удаляет список покупок (вместе со всеми товарами). Требует права write."""
    if not await check_write_permission(list_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    result = await db.execute(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    await db.delete(shopping_list)
    await db.commit()


@router.post("/{list_id}/items", response_model=ListItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_list(
        list_id: int,
        item_data: ListItemCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Добавляет новый товар в указанный список. Требует права write."""
    if not await check_write_permission(list_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    result = await db.execute(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    new_item = ListItem(
        list_id=list_id,
        name=item_data.name,
        quantity=item_data.quantity,
        unit=item_data.unit,
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
    """Обновляет товар. Требует права write."""
    # Сначала получаем список, к которому относится товар
    result = await db.execute(
        select(ListItem).where(ListItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not await check_write_permission(item.list_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    old_completed = item.is_completed

    if item_data.name is not None:
        item.name = item_data.name
    if item_data.quantity is not None:
        item.quantity = item_data.quantity
    if item_data.unit is not None:
        item.unit = item_data.unit
    if item_data.is_completed is not None:
        item.is_completed = item_data.is_completed

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
    """Удаляет товар из списка. Требует права write."""
    result = await db.execute(
        select(ListItem).where(ListItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not await check_write_permission(item.list_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await db.delete(item)
    await db.commit()
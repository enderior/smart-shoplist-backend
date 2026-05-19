from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList
from app.models.list_member import ListMember
from app.schemas.shopping_list import ShoppingListResponse

router = APIRouter(prefix="/shared", tags=["Shared Lists"])


# ========== ПРИГЛАСИТЬ ПОЛЬЗОВАТЕЛЯ ==========
@router.post("/lists/{list_id}/invite/{user_id}")
async def invite_user(
        list_id: int,
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Приглашает пользователя в список (по ID). Только владелец списка."""

    # Проверяем, существует ли список и является ли пользователь владельцем
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found or you are not owner")

    # Находим приглашаемого пользователя
    user_result = await db.execute(select(User).where(User.id == user_id))
    invited_user = user_result.scalar_one_or_none()
    if not invited_user:
        raise HTTPException(status_code=404, detail=f"User with id '{user_id}' not found")

    if invited_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot invite yourself")

    # Проверяем, не добавлен ли уже
    existing = await db.execute(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == invited_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has access to this list")

    # Создаём запись
    member = ListMember(list_id=list_id, user_id=invited_user.id, permission="read")
    db.add(member)
    await db.commit()

    return {"message": f"User '{invited_user.username}' invited to list '{shopping_list.title}'"}


# ========== УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ ИЗ ДОСТУПА ==========
@router.delete("/lists/{list_id}/members/{user_id}")
async def remove_member(
        list_id: int,
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Удаляет пользователя из совместного доступа. Только владелец списка."""

    # Проверяем, что пользователь – владелец
    list_result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    if not list_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="List not found or you are not owner")

    # Удаляем запись
    result = await db.execute(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="User not found in this list")

    await db.delete(member)
    await db.commit()

    return {"message": "User removed from shared access"}


# ========== СПИСОК СОВМЕСТНЫХ СПИСКОВ (ГДЕ УЧАСТВУЕТ ПОЛЬЗОВАТЕЛЬ) ==========
@router.get("/lists", response_model=list[ShoppingListResponse])
async def get_shared_lists(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Возвращает списки, к которым пользователь имеет доступ (но не является владельцем)."""
    result = await db.execute(
        select(ShoppingList)
        .join(ListMember, ListMember.list_id == ShoppingList.id)
        .where(ListMember.user_id == current_user.id)
    )
    shared_lists = result.scalars().all()

    # Ручное преобразование в Pydantic-схемы
    response_lists = [
        ShoppingListResponse(
            id=lst.id,
            title=lst.title,
            description=lst.description,
            owner_id=lst.owner_id,
            is_archived=lst.is_archived,
            created_at=lst.created_at,
            updated_at=lst.updated_at,
            items=[]
        )
        for lst in shared_lists
    ]
    return response_lists

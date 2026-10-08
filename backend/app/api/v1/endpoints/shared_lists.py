from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.shopping_list import ShoppingList
from app.models.list_member import ListMember
from app.schemas.shopping_list import ShoppingListResponse, ListItemResponse
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/shared", tags=["Shared Lists"])


class PermissionUpdate(BaseModel):
    permission: str  # "read" или "write"


@router.post("/lists/{list_id}/invite/{user_id}")
async def invite_user(
        list_id: int,
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found or you are not owner")

    user_result = await db.execute(select(User).where(User.id == user_id))
    invited_user = user_result.scalar_one_or_none()
    if not invited_user:
        raise HTTPException(status_code=404, detail=f"User with id '{user_id}' not found")

    if invited_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot invite yourself")

    existing = await db.execute(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == invited_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has access to this list")

    member = ListMember(list_id=list_id, user_id=invited_user.id, permission="read")
    db.add(member)
    await db.commit()

    return {"message": f"User '{invited_user.username}' invited to list '{shopping_list.title}'"}


class InviteByEmailRequest(BaseModel):
    email: EmailStr


@router.post("/lists/{list_id}/invite", response_model=dict)
async def invite_user_by_email(
        list_id: int,
        data: InviteByEmailRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Приглашает пользователя в список по email. Только владелец списка."""
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    shopping_list = result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found or you are not owner")

    user_result = await db.execute(select(User).where(User.email == data.email))
    invited_user = user_result.scalar_one_or_none()
    if not invited_user:
        raise HTTPException(status_code=404, detail=f"User with email '{data.email}' not found")

    if invited_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot invite yourself")

    existing = await db.execute(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == invited_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has access to this list")

    member = ListMember(list_id=list_id, user_id=invited_user.id, permission="read")
    db.add(member)
    await db.commit()

    return {"message": f"User '{invited_user.username}' invited to list '{shopping_list.title}'"}


@router.delete("/lists/{list_id}/members/{user_id}")
async def remove_member(
        list_id: int,
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Удаляет участника из списка.

    Владелец может убрать любого участника; участник может выйти из списка
    сам (user_id == current_user.id). Владелец из списка не выходит —
    он может удалить его целиком.
    """
    is_self_leave = user_id == current_user.id

    list_result = await db.execute(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )
    shopping_list = list_result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    if is_self_leave:
        if shopping_list.owner_id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Владелец не может покинуть список",
            )
    elif shopping_list.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="List not found or you are not owner")

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
    if is_self_leave:
        return {"message": "You have left the shared list"}
    return {"message": "User removed from shared access"}


@router.get("/lists/{list_id}/members")
async def get_list_members(
        list_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Возвращает участников списка (владелец + соавторы)."""
    list_result = await db.execute(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )
    shopping_list = list_result.scalar_one_or_none()
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    is_owner = shopping_list.owner_id == current_user.id
    member_check = await db.execute(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == current_user.id
        )
    )
    if not is_owner and not member_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="List not found or no access")

    owner_result = await db.execute(select(User).where(User.id == shopping_list.owner_id))
    owner = owner_result.scalar_one_or_none()

    members_result = await db.execute(
        select(User, ListMember)
        .join(ListMember, ListMember.user_id == User.id)
        .where(ListMember.list_id == list_id)
    )
    rows = members_result.all()

    result = []
    if owner:
        result.append({
            "id": owner.id,
            "username": owner.username,
            "email": owner.email,
            "avatar_url": owner.avatar_url,
            "is_owner": True,
        })
    for user, member in rows:
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "is_owner": False,
        })
    return result


@router.get("/lists", response_model=list[ShoppingListResponse])
async def get_shared_lists(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(ShoppingList)
        .join(ListMember, ListMember.list_id == ShoppingList.id)
        .where(ListMember.user_id == current_user.id)
        .options(selectinload(ShoppingList.items))
    )
    shared_lists = result.scalars().all()

    return [
        ShoppingListResponse(
            id=item.id,
            title=item.title,
            owner_id=item.owner_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
            is_owner=item.owner_id == current_user.id,
            items=[ListItemResponse.model_validate(i) for i in item.items],
        )
        for item in shared_lists
    ]


# ========== ИЗМЕНЕНИЕ ПРАВ УЧАСТНИКА ==========
@router.patch("/lists/{list_id}/members/{user_id}")
async def update_member_permission(
        list_id: int,
        user_id: int,
        data: PermissionUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Изменяет права участника в списке. Только владелец списка."""

    # 1. Проверяем, что пользователь – владелец списка
    list_result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.owner_id == current_user.id
        )
    )
    if not list_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="List not found or you are not owner")

    # 2. Проверяем, что участник существует
    member_result = await db.execute(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == user_id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="User not found in this list")

    # 3. Проверяем допустимость нового права
    if data.permission not in ["read", "write"]:
        raise HTTPException(status_code=400, detail="Permission must be 'read' or 'write'")

    # 4. Обновляем право
    member.permission = data.permission
    await db.commit()

    return {"message": f"Permission updated to '{data.permission}' for user {user_id}"}

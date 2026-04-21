import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

# Настройки для аватаров
AVATAR_DIR = "static/avatars"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


# ========== GET ЭНДПОИНТЫ ==========

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Возвращает информацию о текущем авторизованном пользователе."""
    return current_user


@router.get("/", response_model=list[UserResponse])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ========== PATCH /users/me (обновление всех полей) ==========

@router.patch("/me", response_model=UserResponse)
async def update_user(
        user_data: UserUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Обновляет данные текущего пользователя (email, username, phone, birth_date)."""

    if user_data.email is not None:
        # Проверка уникальности email
        existing = await db.execute(select(User).where(User.email == user_data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email уже используется")
        current_user.email = user_data.email

    if user_data.username is not None:
        # Проверка уникальности username
        existing = await db.execute(select(User).where(User.username == user_data.username))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username уже используется")
        current_user.username = user_data.username

    if user_data.phone is not None:
        current_user.phone = user_data.phone
    if user_data.birth_date is not None:
        current_user.birth_date = user_data.birth_date

    await db.commit()
    await db.refresh(current_user)
    return current_user


# ========== ЗАГРУЗКА АВАТАРА ==========

@router.post("/me/avatar")
async def upload_avatar(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Загружает аватар пользователя (сохраняет на сервере)."""

    # 1. Проверяем расширение
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Проверяем размер
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум {MAX_FILE_SIZE // (1024 * 1024)} MB"
        )

    # 3. Создаём папку, если её нет
    os.makedirs(AVATAR_DIR, exist_ok=True)

    # 4. Генерируем уникальное имя
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"user_{current_user.id}_{timestamp}{ext}"
    file_path = os.path.join(AVATAR_DIR, new_filename)

    # 5. Удаляем старый аватар, если есть
    if current_user.avatar_url:
        old_path = os.path.join("static", current_user.avatar_url.lstrip("/static/"))
        if os.path.exists(old_path):
            os.remove(old_path)

    # 6. Сохраняем новый файл
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 7. Сохраняем URL в БД
    avatar_url = f"/static/avatars/{new_filename}"
    current_user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(current_user)

    return {"avatar_url": avatar_url, "message": "Аватар успешно загружен"}


# ========== УДАЛЕНИЕ АВАТАРА ==========

@router.delete("/me/avatar")
async def delete_avatar(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Удаляет аватар пользователя."""

    if current_user.avatar_url:
        file_path = os.path.join("static", current_user.avatar_url.lstrip("/static/"))
        if os.path.exists(file_path):
            os.remove(file_path)
        current_user.avatar_url = None
        await db.commit()

    return {"message": "Аватар удалён"}
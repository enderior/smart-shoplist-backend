from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
import secrets

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken  # новая модель
from app.schemas.user import UserCreate, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя."""
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email или username уже существует"
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        phone=user_data.phone
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"message": "Пользователь успешно зарегистрирован", "user_id": new_user.id}


@router.post("/login", response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """Вход в систему. Принимает username (email) и password."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ========== ВОССТАНОВЛЕНИЕ ПАРОЛЯ ==========

@router.post("/request-reset")
async def request_password_reset(email: str, db: AsyncSession = Depends(get_db)):
    """
    Запрос на сброс пароля.
    Отправляет ссылку для сброса (в реальном проекте — по email).
    """
    # Находим пользователя по email
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()
    if not user:
        # Для безопасности не сообщаем, существует ли пользователь
        return {"message": "Если пользователь с таким email существует, мы отправили ссылку для сброса пароля"}

    # Удаляем старые токены этого пользователя
    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )

    # Генерируем новый токен
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    await db.commit()

    # В реальном проекте здесь должна быть отправка email
    reset_link = f"http://localhost:8000/reset-password?token={token}"
    print(f"🔗 Ссылка для сброса пароля: {reset_link}")  # временно выводим в консоль

    return {"message": "Ссылка для сброса пароля отправлена на ваш email"}


@router.post("/reset-password")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    """
    Сброс пароля по токену.
    """
    # Проверяем токен
    reset_token = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset_token = reset_token.scalar_one_or_none()

    if not reset_token or reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Недействительный или истекший токен"
        )

    # Находим пользователя
    user = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь не найден")

    # Обновляем пароль
    user.hashed_password = get_password_hash(new_password)

    # Удаляем использованный токен
    await db.delete(reset_token)
    await db.commit()

    return {"message": "Пароль успешно изменен"}
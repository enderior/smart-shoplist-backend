from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
import secrets
from pydantic import BaseModel  # <-- ДОБАВЛЯЕМ

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.schemas.user import UserCreate, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ========== СХЕМЫ ДЛЯ ВОССТАНОВЛЕНИЯ ПАРОЛЯ ==========
class ResetRequest(BaseModel):
    email: str

class ResetPasswordData(BaseModel):
    token: str
    new_password: str


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
async def request_password_reset(data: ResetRequest, db: AsyncSession = Depends(get_db)):
    """
    Запрос на сброс пароля.
    Принимает JSON: {"email": "user@example.com"}
    """
    email = data.email
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()
    if not user:
        return {"message": "Если пользователь с таким email существует, мы отправили ссылку для сброса пароля"}

    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    await db.commit()

    reset_link = f"http://localhost:8000/reset-password?token={token}"
    print(f"🔗 Ссылка для сброса пароля: {reset_link}")

    return {"message": "Ссылка для сброса пароля отправлена на ваш email"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordData, db: AsyncSession = Depends(get_db)):
    """
    Сброс пароля по токену.
    Принимает JSON: {"token": "...", "new_password": "..."}
    """
    token = data.token
    new_password = data.new_password

    reset_token = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset_token = reset_token.scalar_one_or_none()

    if not reset_token or reset_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Недействительный или истекший токен"
        )

    user = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь не найден")

    user.hashed_password = get_password_hash(new_password)

    await db.delete(reset_token)
    await db.commit()

    return {"message": "Пароль успешно изменен"}
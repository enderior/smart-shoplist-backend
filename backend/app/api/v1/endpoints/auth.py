from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
import secrets
import random
import logging
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.email_validation import check_mx_record
from app.services.email import send_reset_code_email
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.schemas.user import UserCreate, Token, ResetRequest, ResetPasswordData

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


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
    Генерирует 6-значный код и отправляет его на email.
    """
    email = data.email

    # Мягкая MX-валидация
    if not check_mx_record(email):
        logger.warning(f"Регистрация/сброс с доменом без MX: {email}")

    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()

    if not user:
        # Не раскрываем, существует ли пользователь
        return {"message": "Если пользователь с таким email существует, мы отправили код для сброса пароля"}

    # Удаляем старые токены
    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )

    # Генерируем 6-значный код
    code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    reset_token = PasswordResetToken(
        user_id=user.id,
        code=code,
        expires_at=expires_at,
        attempts=0,
    )
    db.add(reset_token)
    await db.commit()

    # Отправляем код (в dev-режиме печатается в консоль)
    send_reset_code_email(email, code)

    return {"message": "Код для сброса пароля отправлен на ваш email"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordData, db: AsyncSession = Depends(get_db)):
    email = data.email
    code = data.code
    new_password = data.new_password

    # Находим пользователя
    user = await db.execute(select(User).where(User.email == email))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Недействительный код")

    # Находим последний активный токен пользователя
    reset_token = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id)
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = reset_token.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Недействительный код")

    # Проверка попыток
    if reset_token.attempts >= 5:
        raise HTTPException(status_code=400, detail="Слишком много попыток, запросите новый код")

    # Проверка срока
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Код истёк")

    # Проверка кода
    if reset_token.code != code:
        reset_token.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Недействительный код")

    # Всё ок — меняем пароль
    user.hashed_password = get_password_hash(new_password)

    # Удаляем токен
    await db.delete(reset_token)
    await db.commit()

    return {"message": "Пароль успешно изменён"}

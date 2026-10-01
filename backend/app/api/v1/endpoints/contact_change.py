import secrets
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.contact_change_token import ContactChangeToken
from app.schemas.user import (
    UserResponse,
    EmailChangeRequest,
    EmailChangeConfirm,
    PhoneChangeRequest,
    PhoneChangeConfirm,
)
from app.services.email import (
    send_email_change_code_email,
    send_phone_change_code_email,
)

router = APIRouter(prefix="/users/me", tags=["Contact Change"])
logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=15)
MAX_ATTEMPTS = 5


def _gen_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _create_token(
        db: AsyncSession,
        user_id: int,
        change_type: str,
        new_value: str,
) -> str:
    """Удаляет старые токены этого типа и создаёт новый. Возвращает код."""
    await db.execute(
        delete(ContactChangeToken).where(
            ContactChangeToken.user_id == user_id,
            ContactChangeToken.change_type == change_type,
        )
    )

    code = _gen_code()
    token = ContactChangeToken(
        user_id=user_id,
        change_type=change_type,
        new_value=new_value,
        code=code,
        expires_at=datetime.now(timezone.utc) + CODE_TTL,
        attempts=0,
    )
    db.add(token)
    await db.commit()
    return code


async def _verify_token(
        db: AsyncSession,
        user_id: int,
        change_type: str,
        new_value: str,
        code: str,
) -> ContactChangeToken:
    """Проверяет токен. Если код неверный — инкрементирует attempts и кидает 400."""
    result = await db.execute(
        select(ContactChangeToken)
        .where(
            ContactChangeToken.user_id == user_id,
            ContactChangeToken.change_type == change_type,
        )
        .order_by(ContactChangeToken.created_at.desc())
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=400, detail="Нет активного запроса на изменение")

    if token.new_value != new_value:
        raise HTTPException(status_code=400, detail="Значение не совпадает с запрошенным")

    if token.attempts >= MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Слишком много попыток, запросите новый код")

    expires_at = _to_utc(token.expires_at)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Код истёк")

    if token.code != code:
        token.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Недействительный код")

    return token


# ========== EMAIL ==========

@router.post("/email/request-change")
async def request_email_change(
        data: EmailChangeRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    new_email = str(data.new_email)

    if new_email == current_user.email:
        raise HTTPException(status_code=400, detail="Новый email совпадает с текущим")

    existing = await db.execute(select(User).where(User.email == new_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Этот email уже используется")

    code = await _create_token(db, current_user.id, "email", new_email)

    # Код уходит на НОВЫЙ email — так мы убеждаемся, что юзер владеет им
    send_email_change_code_email(new_email, code)

    return {"message": f"Код подтверждения отправлен на {new_email}"}


@router.post("/email/confirm-change", response_model=UserResponse)
async def confirm_email_change(
        data: EmailChangeConfirm,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    new_email = str(data.new_email)

    token = await _verify_token(db, current_user.id, "email", new_email, data.code)

    # Перепроверяем — вдруг email заняли за время, пока юзер вводил код
    existing = await db.execute(select(User).where(User.email == new_email))
    if existing.scalar_one_or_none():
        await db.delete(token)
        await db.commit()
        raise HTTPException(status_code=400, detail="Этот email уже используется")

    current_user.email = new_email
    await db.delete(token)
    await db.commit()
    await db.refresh(current_user)
    return current_user


# ========== PHONE ==========

@router.post("/phone/request-change")
async def request_phone_change(
        data: PhoneChangeRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    new_phone = data.new_phone

    if new_phone == current_user.phone:
        raise HTTPException(status_code=400, detail="Новый телефон совпадает с текущим")

    existing = await db.execute(select(User).where(User.phone == new_phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Этот телефон уже используется")

    code = await _create_token(db, current_user.id, "phone", new_phone)

    # Телефон подтверждаем через ТЕКУЩИЙ email пользователя
    send_phone_change_code_email(current_user.email, code)

    return {"message": f"Код подтверждения отправлен на {current_user.email}"}


@router.post("/phone/confirm-change", response_model=UserResponse)
async def confirm_phone_change(
        data: PhoneChangeConfirm,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    new_phone = data.new_phone

    token = await _verify_token(db, current_user.id, "phone", new_phone, data.code)

    existing = await db.execute(select(User).where(User.phone == new_phone))
    if existing.scalar_one_or_none():
        await db.delete(token)
        await db.commit()
        raise HTTPException(status_code=400, detail="Этот телефон уже используется")

    current_user.phone = new_phone
    await db.delete(token)
    await db.commit()
    await db.refresh(current_user)
    return current_user

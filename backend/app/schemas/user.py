from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional

# Единое правило для пароля во всём API:
#   min_length=6  — защита от пустых и слишком коротких паролей
#   max_length=72 — bcrypt молча обрезает всё, что длиннее 72 байт
PASSWORD_MIN = 6
PASSWORD_MAX = 72


class UserBase(BaseModel):
    email: EmailStr
    username: str
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    birth_date: Optional[date] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    phone: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    birth_date: Optional[date] = None


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


# ========== ВОССТАНОВЛЕНИЕ ПАРОЛЯ ==========

class ResetRequest(BaseModel):
    """Запрос на сброс пароля."""
    email: EmailStr


class ResetPasswordData(BaseModel):
    """Сброс пароля по коду."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


# ========== СМЕНА EMAIL / PHONE С ПОДТВЕРЖДЕНИЕМ ==========

class EmailChangeRequest(BaseModel):
    new_email: EmailStr


class EmailChangeConfirm(BaseModel):
    new_email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class PhoneChangeRequest(BaseModel):
    new_phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')


class PhoneChangeConfirm(BaseModel):
    new_phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    code: str = Field(..., min_length=6, max_length=6)


class Token(BaseModel):
    access_token: str

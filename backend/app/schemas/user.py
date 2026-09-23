from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    username: str
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    birth_date: Optional[date] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str


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
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    birth_date: Optional[date] = None


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str


# ========== ВОССТАНОВЛЕНИЕ ПАРОЛЯ ==========

class ResetRequest(BaseModel):
    """Запрос на сброс пароля. Принимает email."""
    email: EmailStr


class ResetPasswordData(BaseModel):
    """Сброс пароля по коду. Принимает email, код и новый пароль."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None

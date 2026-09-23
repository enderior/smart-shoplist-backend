import pytest
from httpx import AsyncClient
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from sqlalchemy import select
from app.core.database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_request_reset(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "reset@example.com",
        "username": "resetuser",
        "password": "oldpass"
    })
    resp = await client.post("/auth/request-reset", json={"email": "reset@example.com"})
    assert resp.status_code == 200
    assert "код для сброса пароля отправлен" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "reset2@example.com",
        "username": "resetuser2",
        "password": "oldpass"
    })
    await client.post("/auth/request-reset", json={"email": "reset2@example.com"})

    # Получаем код из БД
    async with AsyncSessionLocal() as db:
        token_record = await db.execute(
            select(PasswordResetToken).join(User).where(User.email == "reset2@example.com")
        )
        token_record = token_record.scalar_one_or_none()
        assert token_record is not None
        code = token_record.code

    # Сбрасываем пароль по коду
    resp = await client.post("/auth/reset-password", json={
        "email": "reset2@example.com",
        "code": code,
        "new_password": "newpass123"
    })
    assert resp.status_code == 200
    assert "Пароль успешно изменён" in resp.json()["message"]

    # Проверяем вход с новым паролем
    login_resp = await client.post("/auth/login", data={
        "username": "reset2@example.com",
        "password": "newpass123"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

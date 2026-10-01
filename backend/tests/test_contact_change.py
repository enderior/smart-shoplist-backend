import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User
from app.models.contact_change_token import ContactChangeToken
from app.core.database import AsyncSessionLocal


async def _register_and_login(client: AsyncClient, email: str, username: str, password: str = "pass123"):
    await client.post("/auth/register", json={
        "email": email, "username": username, "password": password,
    })
    resp = await client.post("/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _get_last_code(email: str, change_type: str) -> str:
    """Читает последний код из БД."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ContactChangeToken)
            .join(User, User.id == ContactChangeToken.user_id)
            .where(User.email == email, ContactChangeToken.change_type == change_type)
            .order_by(ContactChangeToken.created_at.desc())
        )
        token = result.scalar_one_or_none()
        assert token is not None, "Токен не создан"
        return token.code


# ========== EMAIL ==========

@pytest.mark.asyncio
async def test_email_change_success(client: AsyncClient):
    headers = await _register_and_login(client, "ec1@example.com", "ec1")
    resp = await client.post(
        "/users/me/email/request-change",
        json={"new_email": "ec1_new@example.com"},
        headers=headers,
    )
    assert resp.status_code == 200

    code = await _get_last_code("ec1@example.com", "email")
    resp = await client.post(
        "/users/me/email/confirm-change",
        json={"new_email": "ec1_new@example.com", "code": code},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "ec1_new@example.com"

    # Логин теперь по новому email
    login = await client.post("/auth/login", data={
        "username": "ec1_new@example.com", "password": "pass123",
    })
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_email_change_wrong_code(client: AsyncClient):
    headers = await _register_and_login(client, "ec2@example.com", "ec2")
    await client.post(
        "/users/me/email/request-change",
        json={"new_email": "ec2_new@example.com"},
        headers=headers,
    )
    resp = await client.post(
        "/users/me/email/confirm-change",
        json={"new_email": "ec2_new@example.com", "code": "000000"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_email_change_same_email(client: AsyncClient):
    headers = await _register_and_login(client, "ec3@example.com", "ec3")
    resp = await client.post(
        "/users/me/email/request-change",
        json={"new_email": "ec3@example.com"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_email_change_taken(client: AsyncClient):
    await _register_and_login(client, "ec4a@example.com", "ec4a")
    headers = await _register_and_login(client, "ec4b@example.com", "ec4b")
    resp = await client.post(
        "/users/me/email/request-change",
        json={"new_email": "ec4a@example.com"},
        headers=headers,
    )
    assert resp.status_code == 400


# ========== PHONE ==========

@pytest.mark.asyncio
async def test_phone_change_success(client: AsyncClient):
    headers = await _register_and_login(client, "pc1@example.com", "pc1")
    resp = await client.post(
        "/users/me/phone/request-change",
        json={"new_phone": "+79001112233"},
        headers=headers,
    )
    assert resp.status_code == 200

    code = await _get_last_code("pc1@example.com", "phone")
    resp = await client.post(
        "/users/me/phone/confirm-change",
        json={"new_phone": "+79001112233", "code": code},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+79001112233"


@pytest.mark.asyncio
async def test_phone_change_wrong_code(client: AsyncClient):
    headers = await _register_and_login(client, "pc2@example.com", "pc2")
    await client.post(
        "/users/me/phone/request-change",
        json={"new_phone": "+79002223344"},
        headers=headers,
    )
    resp = await client.post(
        "/users/me/phone/confirm-change",
        json={"new_phone": "+79002223344", "code": "999999"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_phone_change_taken(client: AsyncClient):
    # Первый регистрируется сразу с телефоном (UserCreate принимает phone)
    await client.post("/auth/register", json={
        "email": "pc3a@example.com",
        "username": "pc3a",
        "password": "pass123",
        "phone": "+79003334455",
    })
    # Второй пытается занять тот же номер
    headers2 = await _register_and_login(client, "pc3b@example.com", "pc3b")
    resp = await client.post(
        "/users/me/phone/request-change",
        json={"new_phone": "+79003334455"},
        headers=headers2,
    )
    assert resp.status_code == 400

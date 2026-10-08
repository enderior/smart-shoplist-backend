import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 201
    assert response.json()["message"] == "Пользователь успешно зарегистрирован"


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    # регистрация
    await client.post("/auth/register", json={
        "email": "login@example.com",
        "username": "loginuser",
        "password": "loginpass"
    })
    # логин (OAuth2 form data)
    response = await client.post("/auth/login", data={
        "username": "login@example.com",
        "password": "loginpass"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    """BUG-018: пароль короче 6 символов → 422."""
    resp = await client.post("/auth/register", json={
        "email": "short@example.com",
        "username": "shortuser",
        "password": "abc"
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_password_empty(client: AsyncClient):
    """BUG-018: пустой пароль → 422."""
    resp = await client.post("/auth/register", json={
        "email": "empty@example.com",
        "username": "emptyuser",
        "password": ""
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_empty_fields(client: AsyncClient):
    """BUG-020: пустые username/password → 422, а не 401."""
    resp = await client.post("/auth/login", data={
        "username": "",
        "password": ""
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reset_password_too_short(client: AsyncClient):
    """BUG-019: новый пароль при сбросе короче 6 символов → 422."""
    await client.post("/auth/register", json={
        "email": "resetcheck@example.com",
        "username": "resetcheck",
        "password": "oldpass123"
    })
    await client.post("/auth/request-reset", json={"email": "resetcheck@example.com"})

    # Код нам всё равно нужен корректной длины, но new_password — короткий
    resp = await client.post("/auth/reset-password", json={
        "email": "resetcheck@example.com",
        "code": "000000",
        "new_password": "abc"
    })
    # 422 придёт раньше, чем проверка кода
    assert resp.status_code == 422

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
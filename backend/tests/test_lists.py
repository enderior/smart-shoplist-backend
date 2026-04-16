import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_list(client: AsyncClient):
    # регистрация
    await client.post("/auth/register", json={
        "email": "list@example.com",
        "username": "listuser",
        "password": "listpass"
    })
    # логин
    login_resp = await client.post("/auth/login", data={
        "username": "list@example.com",
        "password": "listpass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # создание списка
    response = await client.post("/lists/", json={
        "title": "Мой тестовый список",
        "description": "Для теста"
    }, headers=headers)
    assert response.status_code == 201
    assert response.json()["title"] == "Мой тестовый список"
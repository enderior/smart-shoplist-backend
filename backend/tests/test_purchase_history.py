import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_purchase_history_empty(client: AsyncClient):
    # Регистрация нового пользователя
    await client.post("/auth/register", json={
        "email": "history@example.com",
        "username": "historyuser",
        "password": "historypass"
    })
    # Логин
    login_resp = await client.post("/auth/login", data={
        "username": "history@example.com",
        "password": "historypass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # История должна быть пустой
    resp = await client.get("/purchase-history/", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_purchase_history_after_completion(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "history2@example.com",
        "username": "historyuser2",
        "password": "historypass2"
    })
    # Логин
    login_resp = await client.post("/auth/login", data={
        "username": "history2@example.com",
        "password": "historypass2"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список
    list_resp = await client.post("/lists/", json={
        "title": "Тестовый список",
        "description": "Для истории"
    }, headers=headers)
    list_id = list_resp.json()["id"]

    # Добавить товар
    item_resp = await client.post(f"/lists/{list_id}/items", json={
        "name": "Молоко",
        "quantity": 2,
        "unit": "л"
    }, headers=headers)
    item_id = item_resp.json()["id"]

    # Отметить товар как купленный
    await client.put(f"/lists/items/{item_id}", json={
        "is_completed": True
    }, headers=headers)

    # Проверить историю
    history_resp = await client.get("/purchase-history/", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["product_name"] == "Молоко"
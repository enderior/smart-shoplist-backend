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

@pytest.mark.asyncio
async def test_purchase_history_pagination(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "pagin@example.com",
        "username": "paginuser",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "pagin@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список
    list_resp = await client.post("/lists/", json={"title": "Пагинация"}, headers=headers)
    list_id = list_resp.json()["id"]

    # Добавить 5 товаров и отметить их купленными
    item_ids = []
    for i in range(5):
        item = await client.post(f"/lists/{list_id}/items", json={"name": f"Товар {i}"}, headers=headers)
        item_id = item.json()["id"]
        item_ids.append(item_id)
        await client.put(f"/lists/items/{item_id}", json={"is_completed": True}, headers=headers)

    # Запросить первые 2 записи
    resp1 = await client.get("/purchase-history/?skip=0&limit=2", headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1) == 2

    # Запросить следующие 2 (skip=2)
    resp2 = await client.get("/purchase-history/?skip=2&limit=2", headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2) == 2

    # Убедиться, что записи не пересекаются
    ids1 = {item["id"] for item in data1}
    ids2 = {item["id"] for item in data2}
    assert ids1.isdisjoint(ids2)
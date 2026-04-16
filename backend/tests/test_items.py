import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_add_item(client: AsyncClient):
    # Регистрация и логин
    await client.post("/auth/register", json={
        "email": "item@example.com",
        "username": "itemuser",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "item@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список
    list_resp = await client.post("/lists/", json={"title": "Список для товаров"}, headers=headers)
    list_id = list_resp.json()["id"]

    # Добавить товар
    item_resp = await client.post(f"/lists/{list_id}/items", json={
        "name": "Тестовый товар",
        "quantity": 5,
        "unit": "шт"
    }, headers=headers)
    assert item_resp.status_code == 201
    item = item_resp.json()
    assert item["name"] == "Тестовый товар"
    assert item["quantity"] == 5
    assert item["unit"] == "шт"
    assert item["is_completed"] is False

@pytest.mark.asyncio
async def test_update_item_fields(client: AsyncClient):
    # Регистрация и логин
    await client.post("/auth/register", json={
        "email": "update_item@example.com",
        "username": "updateitem",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "update_item@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список и товар
    list_resp = await client.post("/lists/", json={"title": "Список"}, headers=headers)
    list_id = list_resp.json()["id"]
    item_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Товар"}, headers=headers)
    item_id = item_resp.json()["id"]

    # Обновить название и количество
    update_resp = await client.put(f"/lists/items/{item_id}", json={
        "name": "Обновлённый товар",
        "quantity": 10
    }, headers=headers)
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Обновлённый товар"
    assert data["quantity"] == 10

@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient):
    # Регистрация и логин
    await client.post("/auth/register", json={
        "email": "delete_item@example.com",
        "username": "deleteitem",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "delete_item@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список и товар
    list_resp = await client.post("/lists/", json={"title": "Список"}, headers=headers)
    list_id = list_resp.json()["id"]
    item_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Товар на удаление"}, headers=headers)
    item_id = item_resp.json()["id"]

    # Удалить товар
    delete_resp = await client.delete(f"/lists/items/{item_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Попробовать получить удалённый товар (в составе списка)
    list_get = await client.get(f"/lists/{list_id}", headers=headers)
    items = list_get.json()["items"]
    assert not any(i["id"] == item_id for i in items)
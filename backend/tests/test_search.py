import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_suggestions_empty(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "search@example.com",
        "username": "searchuser",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "search@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Пустой запрос
    resp = await client.get("/search/suggestions?q=", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == []

    # Слишком короткий запрос
    resp = await client.get("/search/suggestions?q=х", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == []


@pytest.mark.asyncio
async def test_search_suggestions_from_lists(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "search2@example.com",
        "username": "searchuser2",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "search2@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём список и добавляем ТЕСТОВЫЕ товары
    list_resp = await client.post("/lists/", json={"title": "Тест поиска"}, headers=headers)
    list_id = list_resp.json()["id"]
    await client.post(f"/lists/{list_id}/items", json={"name": "Тестовый продукт для поиска"}, headers=headers)
    await client.post(f"/lists/{list_id}/items", json={"name": "Другой тестовый продукт"}, headers=headers)

    # Поиск
    resp = await client.get("/search/suggestions?q=тестовый", headers=headers)
    assert resp.status_code == 200
    suggestions = resp.json()["suggestions"]

    # Проверяем, что список не пуст
    assert len(suggestions) > 0, "Подсказки не найдены"
    # Проверяем, что в каждом найденном названии есть слово "тестовый"
    assert all("тестовый" in s.lower() for s in suggestions)


@pytest.mark.asyncio
async def test_search_suggestions_from_purchase_history(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "search3@example.com",
        "username": "searchuser3",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "search3@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём список и товар
    list_resp = await client.post("/lists/", json={"title": "Тест истории"}, headers=headers)
    list_id = list_resp.json()["id"]
    item = await client.post(f"/lists/{list_id}/items", json={"name": "Продукт для истории"}, headers=headers)
    item_id = item.json()["id"]

    # Отмечаем как купленный (добавляется в историю)
    await client.put(f"/lists/items/{item_id}", json={"is_completed": True}, headers=headers)
    history_resp = await client.get("/purchase-history/", headers=headers)
    print("HISTORY:", history_resp.json())

    # Поиск
    resp = await client.get("/search/suggestions?q=продукт", headers=headers)
    assert resp.status_code == 200
    suggestions = resp.json()["suggestions"]
    print(f"DEBUG: suggestions = {suggestions}")

    # Проверяем, что список не пуст
    assert len(suggestions) > 0, "Подсказки из истории не найдены"
    # Проверяем, что в названиях есть слово "продукт"
    assert any("продукт" in s.lower() for s in suggestions)

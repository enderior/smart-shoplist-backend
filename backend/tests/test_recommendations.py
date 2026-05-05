import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_recommendations_static(client: AsyncClient):
    # Регистрация пользователя
    await client.post("/auth/register", json={
        "email": "rec@example.com",
        "username": "recuser",
        "password": "recpass"
    })
    # Логин
    login_resp = await client.post("/auth/login", data={
        "username": "rec@example.com",
        "password": "recpass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём список
    list_resp = await client.post("/lists/", json={"title": "Список для рекомендаций"}, headers=headers)
    list_id = list_resp.json()["id"]

    # Добавляем товар "хлеб"
    await client.post(f"/lists/{list_id}/items", json={"name": "хлеб"}, headers=headers)

    # Получаем рекомендации
    resp = await client.get(f"/recommendations/list/{list_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert "list_id" in data
    assert data["list_id"] == list_id
    assert isinstance(data["recommendations"], list)

    # Для "хлеба" должны быть рекомендации (масло, молоко, колбаса...)
    # Проверяем, что список не пуст и не содержит "хлеб"
    assert "хлеб" not in [r.lower() for r in data["recommendations"]]
    assert len(data["recommendations"]) > 0


@pytest.mark.asyncio
async def test_recommendations_exclude_existing_items(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "rec2@example.com",
        "username": "recuser2",
        "password": "recpass2"
    })
    # Логин
    login_resp = await client.post("/auth/login", data={
        "username": "rec2@example.com",
        "password": "recpass2"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём список
    list_resp = await client.post("/lists/", json={"title": "Список с товарами"}, headers=headers)
    list_id = list_resp.json()["id"]

    # Добавляем товар "хлеб"
    await client.post(f"/lists/{list_id}/items", json={"name": "хлеб"}, headers=headers)

    # Добавляем товар "масло" (который мог бы быть в рекомендациях)
    await client.post(f"/lists/{list_id}/items", json={"name": "масло"}, headers=headers)

    # Получаем рекомендации
    resp = await client.get(f"/recommendations/list/{list_id}", headers=headers)
    assert resp.status_code == 200
    recommendations = resp.json()["recommendations"]

    # "масло" не должно быть в рекомендациях, так как уже есть в списке
    assert "масло" not in [r.lower() for r in recommendations]


@pytest.mark.asyncio
async def test_recommendations_nonexistent_list(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "rec3@example.com",
        "username": "recuser3",
        "password": "recpass3"
    })
    # Логин
    login_resp = await client.post("/auth/login", data={
        "username": "rec3@example.com",
        "password": "recpass3"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Запрашиваем рекомендации для несуществующего списка
    resp = await client.get("/recommendations/list/99999", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "List not found"


@pytest.mark.asyncio
async def test_recommendations_empty_list(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "rec4@example.com",
        "username": "recuser4",
        "password": "recpass4"
    })
    # Логин
    login_resp = await client.post("/auth/login", data={
        "username": "rec4@example.com",
        "password": "recpass4"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём пустой список
    list_resp = await client.post("/lists/", json={"title": "Пустой список"}, headers=headers)
    list_id = list_resp.json()["id"]

    # Получаем рекомендации для пустого списка
    resp = await client.get(f"/recommendations/list/{list_id}", headers=headers)
    assert resp.status_code == 200
    recommendations = resp.json()["recommendations"]
    # Для пустого списка рекомендации должны быть пустым массивом
    assert recommendations == []


@pytest.mark.asyncio
async def test_recommendations_with_purchase_history(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "rec_history@example.com",
        "username": "rechist",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "rec_history@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список и добавить товары
    list_resp = await client.post("/lists/", json={"title": "Тест"}, headers=headers)
    list_id = list_resp.json()["id"]
    item1 = await client.post(f"/lists/{list_id}/items", json={"name": "хлеб"}, headers=headers)
    item1_id = item1.json()["id"]
    item2 = await client.post(f"/lists/{list_id}/items", json={"name": "масло"}, headers=headers)
    item2_id = item2.json()["id"]

    # Отметить оба как купленные (добавится история)
    await client.put(f"/lists/items/{item1_id}", json={"is_completed": True}, headers=headers)
    await client.put(f"/lists/items/{item2_id}", json={"is_completed": True}, headers=headers)

    # Создать новый список и добавить только "хлеб"
    list2_resp = await client.post("/lists/", json={"title": "Новый список"}, headers=headers)
    list2_id = list2_resp.json()["id"]
    await client.post(f"/lists/{list2_id}/items", json={"name": "хлеб"}, headers=headers)

    # Получить рекомендации – должно быть масло (из истории)
    rec_resp = await client.get(f"/recommendations/list/{list2_id}", headers=headers)
    assert rec_resp.status_code == 200
    recs = rec_resp.json()["recommendations"]
    assert "масло" in recs

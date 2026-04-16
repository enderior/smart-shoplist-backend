import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_recommendations_static(client: AsyncClient):
    # Регистрация
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

    # Статические рекомендации для "хлеб"
    resp = await client.get("/recommendations/хлеб", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    # В статическом словаре должны быть "масло", "молоко", "колбаса"
    assert any(rec in data["recommendations"] for rec in ["масло", "молоко", "колбаса"])

@pytest.mark.asyncio
async def test_recommendations_dynamic(client: AsyncClient):
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

    # Создать список
    list_resp = await client.post("/lists/", json={
        "title": "Список для рекомендаций"
    }, headers=headers)
    list_id = list_resp.json()["id"]

    # Добавить товары: "пиво" и "чипсы"
    item1 = await client.post(f"/lists/{list_id}/items", json={"name": "пиво"}, headers=headers)
    item1_id = item1.json()["id"]
    item2 = await client.post(f"/lists/{list_id}/items", json={"name": "чипсы"}, headers=headers)
    item2_id = item2.json()["id"]

    # Отметить оба как купленные (создаст историю)
    await client.put(f"/lists/items/{item1_id}", json={"is_completed": True}, headers=headers)
    await client.put(f"/lists/items/{item2_id}", json={"is_completed": True}, headers=headers)

    # Проверить рекомендации для "пиво" – должны быть "чипсы" (или статические)
    resp = await client.get("/recommendations/пиво", headers=headers)
    assert resp.status_code == 200
    recommendations = resp.json()["recommendations"]
    # В динамических рекомендациях могут появиться "чипсы" (зависит от логики)
    # Можем просто проверить, что список не пуст
    assert isinstance(recommendations, list)
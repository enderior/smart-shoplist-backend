import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_to_favorites(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "fav@example.com",
        "username": "favuser",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "fav@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список и товар
    list_resp = await client.post("/lists/", json={"title": "Тестовый список"}, headers=headers)
    list_id = list_resp.json()["id"]
    item_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Тестовый товар"}, headers=headers)
    item_id = item_resp.json()["id"]

    # Добавить в избранное
    fav_resp = await client.post(f"/favorites/{item_id}", headers=headers)
    assert fav_resp.status_code == 201
    assert fav_resp.json()["message"] == "Товар добавлен в избранное"

    # Получить список избранного
    get_resp = await client.get("/favorites/", headers=headers)
    assert get_resp.status_code == 200
    favorites = get_resp.json()
    assert len(favorites) == 1
    assert favorites[0]["item_id"] == item_id

    # Удалить из избранного
    del_resp = await client.delete(f"/favorites/{item_id}", headers=headers)
    assert del_resp.status_code == 204

    # Проверить, что избранное пусто
    get_resp = await client.get("/favorites/", headers=headers)
    assert len(get_resp.json()) == 0


@pytest.mark.asyncio
async def test_add_to_favorites_duplicate(client: AsyncClient):
    # Регистрация и логин
    await client.post("/auth/register", json={
        "email": "fav2@example.com",
        "username": "favuser2",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "fav2@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список и товар
    list_resp = await client.post("/lists/", json={"title": "Список"}, headers=headers)
    list_id = list_resp.json()["id"]
    item_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Товар"}, headers=headers)
    item_id = item_resp.json()["id"]

    # Добавить в избранное дважды
    await client.post(f"/favorites/{item_id}", headers=headers)
    fav_resp = await client.post(f"/favorites/{item_id}", headers=headers)
    assert fav_resp.status_code == 400
    assert "уже в избранном" in fav_resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_nonexistent_item_to_favorites(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "fav3@example.com",
        "username": "favuser3",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "fav3@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fav_resp = await client.post("/favorites/99999", headers=headers)
    assert fav_resp.status_code == 404
    assert fav_resp.json()["detail"] == "Товар не найден"

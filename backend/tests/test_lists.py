import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_update_list(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "update_list@example.com",
        "username": "updatelist",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "update_list@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список
    create_resp = await client.post("/lists/", json={
        "title": "Старое название",
        "description": "Старое описание"
    }, headers=headers)
    list_id = create_resp.json()["id"]

    # Обновить список
    update_resp = await client.put(f"/lists/{list_id}", json={
        "title": "Новое название",
        "description": "Новое описание"
    }, headers=headers)
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["title"] == "Новое название"
    assert data["description"] == "Новое описание"

@pytest.mark.asyncio
async def test_delete_list(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "delete_list@example.com",
        "username": "deletelist",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "delete_list@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создать список
    create_resp = await client.post("/lists/", json={
        "title": "Список для удаления"
    }, headers=headers)
    list_id = create_resp.json()["id"]

    # Удалить список
    delete_resp = await client.delete(f"/lists/{list_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Попробовать получить удалённый список (должен быть 404)
    get_resp = await client.get(f"/lists/{list_id}", headers=headers)
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_access_other_user_list(client: AsyncClient):
    # Регистрация первого пользователя
    await client.post("/auth/register", json={
        "email": "user1@example.com",
        "username": "user1",
        "password": "pass1"
    })
    login1 = await client.post("/auth/login", data={
        "username": "user1@example.com",
        "password": "pass1"
    })
    token1 = login1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Создать список от первого пользователя
    list_resp = await client.post("/lists/", json={"title": "Список user1"}, headers=headers1)
    list_id = list_resp.json()["id"]

    # Регистрация второго пользователя
    await client.post("/auth/register", json={
        "email": "user2@example.com",
        "username": "user2",
        "password": "pass2"
    })
    login2 = await client.post("/auth/login", data={
        "username": "user2@example.com",
        "password": "pass2"
    })
    token2 = login2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Второй пользователь пытается получить чужой список
    get_resp = await client.get(f"/lists/{list_id}", headers=headers2)
    assert get_resp.status_code == 404   # или 403, смотря как реализовано

    # Попытка обновить чужой список
    put_resp = await client.put(f"/lists/{list_id}", json={"title": "hack"}, headers=headers2)
    assert put_resp.status_code == 404

    # Попытка удалить чужой список
    del_resp = await client.delete(f"/lists/{list_id}", headers=headers2)
    assert del_resp.status_code == 404
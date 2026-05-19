import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_invite_and_shared_list(client: AsyncClient):
    # 1. Регистрируем владельца
    await client.post("/auth/register", json={
        "email": "owner@example.com",
        "username": "owner",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Регистрируем гостя
    await client.post("/auth/register", json={
        "email": "guest@example.com",
        "username": "guest",
        "password": "pass123"
    })
    login_guest = await client.post("/auth/login", data={
        "username": "guest@example.com",
        "password": "pass123"
    })
    guest_token = login_guest.json()["access_token"]
    guest_headers = {"Authorization": f"Bearer {guest_token}"}

    # 3. Владелец создаёт список
    list_resp = await client.post("/lists/", json={
        "title": "Совместный список",
        "description": "Тестовый список"
    }, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # 4. Владелец приглашает гостя (нужно узнать guest_id)
    users_resp = await client.get("/users/", headers=owner_headers)
    guest_id = None
    for user in users_resp.json():
        if user["username"] == "guest":
            guest_id = user["id"]
            break
    assert guest_id is not None

    invite_resp = await client.post(f"/shared/lists/{list_id}/invite/{guest_id}", headers=owner_headers)
    assert invite_resp.status_code == 200
    assert "invited" in invite_resp.json()["message"]

    # 5. Гость получает список совместных списков
    shared_resp = await client.get("/shared/lists", headers=guest_headers)
    assert shared_resp.status_code == 200
    shared_lists = shared_resp.json()
    assert len(shared_lists) == 1
    assert shared_lists[0]["title"] == "Совместный список"

    # 6. Гость получает все свои списки (должен видеть и совместный)
    all_lists_resp = await client.get("/lists/", headers=guest_headers)
    all_lists = all_lists_resp.json()
    assert any(lst["title"] == "Совместный список" for lst in all_lists)

    # 7. Гость НЕ может удалить чужой список
    delete_resp = await client.delete(f"/lists/{list_id}", headers=guest_headers)
    assert delete_resp.status_code == 404  # или 403

    # 8. Владелец удаляет гостя из доступа
    remove_resp = await client.delete(f"/shared/lists/{list_id}/members/{guest_id}", headers=owner_headers)
    assert remove_resp.status_code == 200

    # 9. Гость больше не видит список в /shared/lists
    shared_resp2 = await client.get("/shared/lists", headers=guest_headers)
    assert shared_resp2.status_code == 200
    assert len(shared_resp2.json()) == 0

    # 10. Гость не видит список и в общем списке
    all_lists_resp2 = await client.get("/lists/", headers=guest_headers)
    assert not any(lst["title"] == "Совместный список" for lst in all_lists_resp2.json())


@pytest.mark.asyncio
async def test_invite_nonexistent_user(client: AsyncClient):
    # Регистрируем владельца
    await client.post("/auth/register", json={
        "email": "owner2@example.com",
        "username": "owner2",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner2@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Создаём список
    list_resp = await client.post("/lists/", json={
        "title": "Тестовый список",
        "description": "Для проверки приглашения несуществующего пользователя"
    }, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # Приглашаем несуществующего пользователя (ID=99999)
    invite_resp = await client.post(f"/shared/lists/{list_id}/invite/99999", headers=owner_headers)
    assert invite_resp.status_code == 404
    assert "not found" in invite_resp.json()["detail"]


@pytest.mark.asyncio
async def test_invite_self(client: AsyncClient):
    # Регистрируем владельца
    await client.post("/auth/register", json={
        "email": "owner3@example.com",
        "username": "owner3",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner3@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Создаём список
    list_resp = await client.post("/lists/", json={
        "title": "Тестовый список",
        "description": "Для проверки самоприглашения"
    }, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # Находим свой user_id
    me_resp = await client.get("/users/me", headers=owner_headers)
    my_id = me_resp.json()["id"]

    # Приглашаем самого себя
    invite_resp = await client.post(f"/shared/lists/{list_id}/invite/{my_id}", headers=owner_headers)
    assert invite_resp.status_code == 400
    assert "cannot invite yourself" in invite_resp.json()["detail"]

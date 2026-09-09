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
        "title": "Совместный список"
    }, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # 4. Находим ID гостя
    users_resp = await client.get("/users/", headers=owner_headers)
    guest_id = None
    for user in users_resp.json():
        if user["username"] == "guest":
            guest_id = user["id"]
            break
    assert guest_id is not None

    # 5. Владелец приглашает гостя
    invite_resp = await client.post(f"/shared/lists/{list_id}/invite/{guest_id}", headers=owner_headers)
    assert invite_resp.status_code == 200
    assert "invited" in invite_resp.json()["message"]

    # 6. Гость получает список совместных списков
    shared_resp = await client.get("/shared/lists", headers=guest_headers)
    assert shared_resp.status_code == 200
    shared_lists = shared_resp.json()
    assert len(shared_lists) == 1
    assert shared_lists[0]["title"] == "Совместный список"

    # 7. Гость получает все свои списки (должен видеть и совместный)
    all_lists_resp = await client.get("/lists/", headers=guest_headers)
    all_lists = all_lists_resp.json()
    assert any(lst["title"] == "Совместный список" for lst in all_lists)

    # 8. Гость НЕ может удалить чужой список (403, так как нет прав write)
    delete_resp = await client.delete(f"/lists/{list_id}", headers=guest_headers)
    assert delete_resp.status_code == 403

    # 9. Владелец удаляет гостя из доступа
    remove_resp = await client.delete(f"/shared/lists/{list_id}/members/{guest_id}", headers=owner_headers)
    assert remove_resp.status_code == 200

    # 10. Гость больше не видит список в /shared/lists
    shared_resp2 = await client.get("/shared/lists", headers=guest_headers)
    assert shared_resp2.status_code == 200
    assert len(shared_resp2.json()) == 0

    # 11. Гость не видит список и в общем списке
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
        "title": "Тестовый список"
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
        "title": "Тестовый список"
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


@pytest.mark.asyncio
async def test_update_member_permission(client: AsyncClient):
    # Регистрация владельца
    await client.post("/auth/register", json={
        "email": "owner_perm@example.com",
        "username": "owner_perm",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner_perm@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Регистрация участника
    await client.post("/auth/register", json={
        "email": "member_perm@example.com",
        "username": "member_perm",
        "password": "pass123"
    })
    login_member = await client.post("/auth/login", data={
        "username": "member_perm@example.com",
        "password": "pass123"
    })
    member_token = login_member.json()["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Владелец создаёт список
    list_resp = await client.post("/lists/", json={
        "title": "Список для прав"
    }, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # Найти ID участника
    users_resp = await client.get("/users/", headers=owner_headers)
    member_id = None
    for user in users_resp.json():
        if user["username"] == "member_perm":
            member_id = user["id"]
            break
    assert member_id is not None

    # Владелец приглашает участника
    invite_resp = await client.post(f"/shared/lists/{list_id}/invite/{member_id}", headers=owner_headers)
    assert invite_resp.status_code == 200

    # Владелец меняет права участника на "write"
    patch_resp = await client.patch(f"/shared/lists/{list_id}/members/{member_id}", json={
        "permission": "write"
    }, headers=owner_headers)
    assert patch_resp.status_code == 200

    # Проверяем, что участник может редактировать (добавить товар)
    add_item_resp = await client.post(f"/lists/{list_id}/items", json={
        "name": "Товар от участника",
        "quantity": 1
    }, headers=member_headers)
    assert add_item_resp.status_code == 201

    # Владелец меняет права на "read"
    patch_resp = await client.patch(f"/shared/lists/{list_id}/members/{member_id}", json={
        "permission": "read"
    }, headers=owner_headers)
    assert patch_resp.status_code == 200

    # Проверяем, что участник не может редактировать
    add_item_resp2 = await client.post(f"/lists/{list_id}/items", json={
        "name": "Попытка добавления"
    }, headers=member_headers)
    assert add_item_resp2.status_code == 403


@pytest.mark.asyncio
async def test_update_permission_not_owner(client: AsyncClient):
    # Регистрация владельца
    await client.post("/auth/register", json={
        "email": "owner_not@example.com",
        "username": "owner_not",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner_not@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Регистрация обычного пользователя
    await client.post("/auth/register", json={
        "email": "not_owner@example.com",
        "username": "not_owner",
        "password": "pass123"
    })
    login_not = await client.post("/auth/login", data={
        "username": "not_owner@example.com",
        "password": "pass123"
    })
    not_token = login_not.json()["access_token"]
    not_headers = {"Authorization": f"Bearer {not_token}"}

    # Владелец создаёт список
    list_resp = await client.post("/lists/", json={
        "title": "Список для теста"
    }, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # Приглашаем пользователя not_owner
    users_resp = await client.get("/users/", headers=owner_headers)
    not_id = None
    for user in users_resp.json():
        if user["username"] == "not_owner":
            not_id = user["id"]
            break
    assert not_id is not None
    await client.post(f"/shared/lists/{list_id}/invite/{not_id}", headers=owner_headers)

    # Пользователь not_owner пытается изменить права (должен получить 404 или 403)
    patch_resp = await client.patch(f"/shared/lists/{list_id}/members/{not_id}", json={
        "permission": "write"
    }, headers=not_headers)
    assert patch_resp.status_code == 404  # или 403, так как он не владелец


@pytest.mark.asyncio
async def test_write_permission_can_update_item(client: AsyncClient):
    # Регистрация владельца
    await client.post("/auth/register", json={
        "email": "owner_write@example.com",
        "username": "owner_write",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner_write@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Регистрация участника
    await client.post("/auth/register", json={
        "email": "member_write@example.com",
        "username": "member_write",
        "password": "pass123"
    })
    login_member = await client.post("/auth/login", data={
        "username": "member_write@example.com",
        "password": "pass123"
    })
    member_token = login_member.json()["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Владелец создаёт список и товар
    list_resp = await client.post("/lists/", json={"title": "Тест"}, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]
    item_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Товар"}, headers=owner_headers)
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    # Найти ID участника
    users_resp = await client.get("/users/", headers=owner_headers)
    member_id = None
    for user in users_resp.json():
        if user["username"] == "member_write":
            member_id = user["id"]
            break
    assert member_id is not None

    # Пригласить и дать права write
    await client.post(f"/shared/lists/{list_id}/invite/{member_id}", headers=owner_headers)
    await client.patch(f"/shared/lists/{list_id}/members/{member_id}", json={"permission": "write"},
                       headers=owner_headers)

    # Участник обновляет товар
    update_resp = await client.put(f"/lists/items/{item_id}", json={"name": "Обновлённый товар"},
                                   headers=member_headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Обновлённый товар"

    # Участник удаляет товар
    delete_resp = await client.delete(f"/lists/items/{item_id}", headers=member_headers)
    assert delete_resp.status_code == 204

    # Участник добавляет новый товар
    add_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Новый товар"}, headers=member_headers)
    assert add_resp.status_code == 201


@pytest.mark.asyncio
async def test_read_permission_cannot_update_item(client: AsyncClient):
    # Регистрация владельца
    await client.post("/auth/register", json={
        "email": "owner_read@example.com",
        "username": "owner_read",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner_read@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Регистрация участника
    await client.post("/auth/register", json={
        "email": "member_read@example.com",
        "username": "member_read",
        "password": "pass123"
    })
    login_member = await client.post("/auth/login", data={
        "username": "member_read@example.com",
        "password": "pass123"
    })
    member_token = login_member.json()["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Владелец создаёт список и товар
    list_resp = await client.post("/lists/", json={"title": "Тест"}, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]
    item_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Товар"}, headers=owner_headers)
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    # Найти ID участника
    users_resp = await client.get("/users/", headers=owner_headers)
    member_id = None
    for user in users_resp.json():
        if user["username"] == "member_read":
            member_id = user["id"]
            break
    assert member_id is not None

    # Пригласить (по умолчанию read)
    await client.post(f"/shared/lists/{list_id}/invite/{member_id}", headers=owner_headers)

    # Участник пытается обновить товар
    update_resp = await client.put(f"/lists/items/{item_id}", json={"name": "Попытка"}, headers=member_headers)
    assert update_resp.status_code == 403

    # Участник пытается удалить товар
    delete_resp = await client.delete(f"/lists/items/{item_id}", headers=member_headers)
    assert delete_resp.status_code == 403

    # Участник пытается добавить товар
    add_resp = await client.post(f"/lists/{list_id}/items", json={"name": "Новый"}, headers=member_headers)
    assert add_resp.status_code == 403


@pytest.mark.asyncio
async def test_write_permission_can_delete_list(client: AsyncClient):
    # Регистрация владельца
    await client.post("/auth/register", json={
        "email": "owner_del@example.com",
        "username": "owner_del",
        "password": "pass123"
    })
    login_owner = await client.post("/auth/login", data={
        "username": "owner_del@example.com",
        "password": "pass123"
    })
    owner_token = login_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Регистрация участника
    await client.post("/auth/register", json={
        "email": "member_del@example.com",
        "username": "member_del",
        "password": "pass123"
    })
    login_member = await client.post("/auth/login", data={
        "username": "member_del@example.com",
        "password": "pass123"
    })
    member_token = login_member.json()["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Владелец создаёт список
    list_resp = await client.post("/lists/", json={"title": "Тест"}, headers=owner_headers)
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # Найти ID участника
    users_resp = await client.get("/users/", headers=owner_headers)
    member_id = None
    for user in users_resp.json():
        if user["username"] == "member_del":
            member_id = user["id"]
            break
    assert member_id is not None

    # Пригласить и дать права write
    await client.post(f"/shared/lists/{list_id}/invite/{member_id}", headers=owner_headers)
    await client.patch(f"/shared/lists/{list_id}/members/{member_id}", json={"permission": "write"},
                       headers=owner_headers)

    # Участник удаляет список
    delete_resp = await client.delete(f"/lists/{list_id}", headers=member_headers)
    assert delete_resp.status_code == 204

    # Проверяем, что список действительно удалён
    get_resp = await client.get(f"/lists/{list_id}", headers=member_headers)
    assert get_resp.status_code == 404

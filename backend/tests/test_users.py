import pytest
from httpx import AsyncClient
from datetime import date


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient):
    # Регистрация
    await client.post("/auth/register", json={
        "email": "update@example.com",
        "username": "updateuser",
        "password": "pass123"
    })
    # Логин
    login_resp = await client.post("/auth/login", data={
        "username": "update@example.com",
        "password": "pass123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Обновление всех полей
    new_data = {
        "email": "newemail@example.com",
        "username": "newusername",
        "phone": "+79991112233",
        "birth_date": "1990-01-01"
    }
    resp = await client.patch("/users/me", json=new_data, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "newemail@example.com"
    assert data["username"] == "newusername"
    assert data["phone"] == "+79991112233"
    assert data["birth_date"] == "1990-01-01"


@pytest.mark.asyncio
async def test_update_user_unique_email(client: AsyncClient):
    # Регистрация первого пользователя
    await client.post("/auth/register", json={
        "email": "first@example.com",
        "username": "first",
        "password": "pass"
    })
    # Регистрация второго
    await client.post("/auth/register", json={
        "email": "second@example.com",
        "username": "second",
        "password": "pass"
    })
    # Логин второго
    login_resp = await client.post("/auth/login", data={
        "username": "second@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Попытка сменить email на уже существующий
    resp = await client.patch("/users/me", json={"email": "first@example.com"}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Email уже используется"


@pytest.mark.asyncio
async def test_update_user_unique_username(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "a@example.com",
        "username": "user_a",
        "password": "pass"
    })
    await client.post("/auth/register", json={
        "email": "b@example.com",
        "username": "user_b",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "b@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch("/users/me", json={"username": "user_a"}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username уже используется"


@pytest.mark.asyncio
async def test_upload_avatar(client: AsyncClient):
    # Регистрация и логин
    await client.post("/auth/register", json={
        "email": "avatar@example.com",
        "username": "avataruser",
        "password": "pass"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "avatar@example.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём тестовый файл (PNG заглушка)
    test_file_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'
    files = {"file": ("test.png", test_file_content, "image/png")}
    resp = await client.post("/users/me/avatar", headers=headers, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "avatar_url" in data
    assert data["avatar_url"].startswith("/static/avatars/")

    # Проверяем, что аватар сохранился в БД
    user_resp = await client.get("/users/me", headers=headers)
    assert user_resp.json()["avatar_url"] == data["avatar_url"]

    # Удаляем аватар
    del_resp = await client.delete("/users/me/avatar", headers=headers)
    assert del_resp.status_code == 200
    user_resp = await client.get("/users/me", headers=headers)
    assert user_resp.json()["avatar_url"] is None

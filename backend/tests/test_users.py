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

    # 1. Обновляем только username
    resp1 = await client.patch("/users/me", json={
        "username": "newusername"
    }, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["username"] == "newusername"
    assert data1["email"] == "update@example.com"  # email не изменился

    # 2. Обновляем только birth_date
    resp2 = await client.patch("/users/me", json={
        "birth_date": "1990-01-01"
    }, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["birth_date"] == "1990-01-01"
    assert data2["username"] == "newusername"  # username не изменился

    # 3. Обновляем оба поля сразу
    resp3 = await client.patch("/users/me", json={
        "username": "fullupdate",
        "birth_date": "1995-05-05"
    }, headers=headers)
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["username"] == "fullupdate"
    assert data3["birth_date"] == "1995-05-05"


@pytest.mark.asyncio
async def test_update_user_unique_username(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "a@example.com",
        "username": "user_a",
        "password": "pass123"
    })
    await client.post("/auth/register", json={
        "email": "b@example.com",
        "username": "user_b",
        "password": "pass123"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "b@example.com",
        "password": "pass123"
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
        "password": "pass123"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "avatar@example.com",
        "password": "pass123"
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


# ========== ТЕСТЫ ДЛЯ СМЕНЫ ПАРОЛЯ ==========

@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient):
    """Успешная смена пароля."""
    await client.post("/auth/register", json={
        "email": "changepass@example.com",
        "username": "changepass",
        "password": "oldpass123"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "changepass@example.com",
        "password": "oldpass123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Меняем пароль
    resp = await client.put("/users/me/password", json={
        "old_password": "oldpass123",
        "new_password": "newpass456"
    }, headers=headers)
    assert resp.status_code == 200
    assert "успешно изменён" in resp.json()["message"]

    # Проверяем, что со старым паролем войти нельзя
    old_login = await client.post("/auth/login", data={
        "username": "changepass@example.com",
        "password": "oldpass123"
    })
    assert old_login.status_code == 401

    # Проверяем, что с новым паролем вход работает
    new_login = await client.post("/auth/login", data={
        "username": "changepass@example.com",
        "password": "newpass456"
    })
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


@pytest.mark.asyncio
async def test_change_password_wrong_old(client: AsyncClient):
    """Неверный старый пароль — ошибка 400."""
    await client.post("/auth/register", json={
        "email": "wrongold@example.com",
        "username": "wrongold",
        "password": "correct"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "wrongold@example.com",
        "password": "correct"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.put("/users/me/password", json={
        "old_password": "incorrect",
        "new_password": "newpass456"
    }, headers=headers)
    assert resp.status_code == 400
    assert "Неверный текущий пароль" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_same_as_old(client: AsyncClient):
    """Новый пароль совпадает со старым — ошибка 400."""
    await client.post("/auth/register", json={
        "email": "samepass@example.com",
        "username": "samepass",
        "password": "samepass123"
    })
    login_resp = await client.post("/auth/login", data={
        "username": "samepass@example.com",
        "password": "samepass123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.put("/users/me/password", json={
        "old_password": "samepass123",
        "new_password": "samepass123"
    }, headers=headers)
    assert resp.status_code == 400
    assert "должен отличаться" in resp.json()["detail"]
    assert "должен отличаться" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_me_ignores_email_and_phone(client: AsyncClient):
    """PATCH /users/me не должен менять email/phone, даже если их передать."""
    await client.post("/auth/register", json={
        "email": "immutable@example.com",
        "username": "immutable",
        "password": "pass123"
    })
    login = await client.post("/auth/login", data={
        "username": "immutable@example.com",
        "password": "pass123"
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.patch("/users/me", json={
        "username": "immutable2",
        "email": "hacked@example.com",  # должно быть проигнорировано
        "phone": "+79999999999",  # должно быть проигнорировано
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "immutable2"
    assert data["email"] == "immutable@example.com"  # не изменился
    assert data["phone"] is None  # не изменился

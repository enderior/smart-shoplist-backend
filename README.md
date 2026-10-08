# Smart ShopList Backend

Бэкенд для «умного» списка покупок на **FastAPI**.
Поддерживает JWT-аутентификацию, управление списками и товарами, совместный доступ, историю покупок, автодополнение поиска и базовые «умные» рекомендации.

[![Run tests](https://github.com/enderior/smart-shoplist-backend/actions/workflows/tests.yml/badge.svg)](https://github.com/enderior/smart-shoplist-backend/actions/workflows/tests.yml)

## 📖 Содержание

- [Технологии](#технологии)
- [Установка и запуск](#установка-и-запуск)
- [API Эндпоинты](#api-эндпоинты)
- [Схема базы данных](#схема-базы-данных)
- [Тестирование](#тестирование)
- [CI/CD](#cicd)
- [Структура проекта](#структура-проекта)

## 🛠 Технологии

- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0 (async)** — ORM
- **PostgreSQL** — база данных
- **Alembic** — миграции
- **Pydantic v2** — валидация данных
- **python-jose** — JWT-токены
- **bcrypt** — хеширование паролей
- **dnspython** — MX-валидация email
- **pytest + httpx** — тестирование (SQLite in-memory)
- **GitHub Actions** — CI/CD

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/enderior/smart-shoplist-backend.git
cd smart-shoplist-backend
```

### 2. Виртуальное окружение и зависимости

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 3. Переменные окружения

Создай файл `backend/.env` (он в `.gitignore`, в репозиторий не попадает):

```env
PROJECT_NAME="Smart ShopList API"
VERSION="1.0.0"
DEBUG=True

SECRET_KEY="<сгенерируй: python -c 'import secrets; print(secrets.token_urlsafe(32))'>"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=10080

DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smartlist

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smartlist

# SMTP для восстановления пароля (опционально).
# Если не заполнено — код печатается в консоль (dev-режим).
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=your_email@yandex.ru
SMTP_PASSWORD=your_app_password
MAIL_FROM=your_email@yandex.ru
MAIL_FROM_NAME="Smart ShopList"
```

### 4. Подготовка базы данных

Убедись, что PostgreSQL запущен. Создай БД.

Для Linux:

```sql
CREATE DATABASE smartlist WITH ENCODING='UTF8' LC_COLLATE='ru_RU.utf8' LC_CTYPE='ru_RU.utf8' TEMPLATE=template0;
```

Для Windows:

```sql
CREATE DATABASE smartlist WITH ENCODING='UTF8'
    LC_COLLATE='Russian_Russia.1251'
    LC_CTYPE='Russian_Russia.1251'
    TEMPLATE=template0;
```

Примени миграции:

```bash
alembic upgrade head
```

Alembic читает URL из `.env` через `settings.async_database_url` — править `alembic.ini` вручную не нужно.

### 5. Запуск сервера

```bash
python run.py
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📡 API Эндпоинты

### Аутентификация

| Метод | Эндпоинт | Описание |
| :--- | :--- | :--- |
| POST | `/auth/register` | Регистрация (мягкая MX-валидация email) |
| POST | `/auth/login` | Вход (OAuth2 form-data), возвращает JWT |
| POST | `/auth/request-reset` | Запрос 6-значного кода на email |
| POST | `/auth/reset-password` | Сброс пароля по коду (защита от брутфорса: 5 попыток) |

### Пользователи

| Метод | Эндпоинт | Описание | Токен |
| :--- | :--- | :--- | :--- |
| GET | `/users/me` | Текущий пользователь | ✅ |
| PATCH | `/users/me` | Обновление профиля (email, username, phone, birth_date) | ✅ |
| PUT | `/users/me/password` | Смена пароля (с проверкой старого) | ✅ |
| POST | `/users/me/avatar` | Загрузка аватара (PNG/JPG/WEBP, ≤ 5 МБ) | ✅ |
| DELETE | `/users/me/avatar` | Удаление аватара | ✅ |
| GET | `/users/` | Список всех пользователей | ❌ |
| GET | `/users/{id}` | Пользователь по ID | ❌ |

### Списки покупок

| Метод | Эндпоинт | Описание | Токен |
| :--- | :--- | :--- | :--- |
| POST | `/lists/` | Создать список | ✅ |
| GET | `/lists/` | Свои + совместные списки | ✅ |
| GET | `/lists/{id}` | Список с товарами | ✅ |
| PUT | `/lists/{id}` | Переименовать (нужно право `write`) | ✅ |
| DELETE | `/lists/{id}` | Удалить (каскадно) | ✅ |

### Товары

| Метод | Эндпоинт | Описание | Токен |
| :--- | :--- | :--- | :--- |
| POST | `/lists/{list_id}/items` | Добавить товар | ✅ |
| PUT | `/lists/items/{item_id}` | Обновить (кол-во, `is_completed` и т.д.) | ✅ |
| DELETE | `/lists/items/{item_id}` | Удалить товар | ✅ |

> При добавлении товара автоматически обновляются `search_history`, `products` и `purchase_history` (регистронезависимо).

### Совместный доступ

| Метод | Эндпоинт | Описание | Токен |
| :--- | :--- | :--- | :--- |
| POST | `/shared/lists/{list_id}/invite/{user_id}` | Пригласить пользователя | ✅ |
| GET | `/shared/lists` | Списки, где я участник | ✅ |
| PATCH | `/shared/lists/{list_id}/members/{user_id}` | Сменить права (`read` / `write`) | ✅ |
| DELETE | `/shared/lists/{list_id}/members/{user_id}` | Убрать участника | ✅ |

### Поиск и рекомендации

| Метод | Эндпоинт | Описание | Токен |
| :--- | :--- | :--- | :--- |
| GET | `/search/suggestions?q=...&limit=5` | Автодополнение по спискам + истории + глобальной базе | ✅ |
| GET | `/recommendations/list/{list_id}` | Топ-5 рекомендаций (статика + история) | ✅ |
| GET | `/purchase-history/?skip=&limit=` | История покупок с пагинацией | ✅ |

### Служебные

| Метод | Эндпоинт | Описание |
| :--- | :--- | :--- |
| GET | `/` | Информация о сервисе |
| GET | `/health` | Healthcheck |

## 🗄 Схема базы данных

https://docs/database_schema.png

Диаграмма создана в `dbdiagram.io`.

### Таблицы

| Таблица | Назначение |
| :--- | :--- |
| `users` | Пользователи (email, username, phone, hashed_password, birth_date, avatar_url) |
| `shopping_lists` | Списки покупок (title, owner_id) |
| `list_items` | Товары в списке (name, quantity, unit, is_completed) |
| `list_members` | Участники совместных списков (permission: `read` / `write`) |
| `purchase_history` | История покупок (user_id, product_name, purchased_at). Уникальна по `(user_id, product_name)` |
| `search_history` | Личная история поиска. Уникальна по `(user_id, product_name)` |
| `products` | Глобальный справочник товаров (`normalized_name` — unique) |
| `password_reset_tokens` | Одноразовые коды сброса пароля (code, expires_at, attempts) |

### Связи

- `shopping_lists.owner_id` → `users.id`
- `list_items.list_id` → `shopping_lists.id`
- `list_members.list_id` → `shopping_lists.id`, `list_members.user_id` → `users.id`
- `purchase_history.user_id` → `users.id`
- `search_history.user_id` → `users.id` (CASCADE)
- `password_reset_tokens.user_id` → `users.id`

## 🧪 Тестирование

Тесты используют отдельную SQLite in-memory БД, реальный Postgres не требуется.

```bash
cd backend
pytest -v
```

Покрытие (41 тест):

- регистрация и логин,
- сброс пароля по коду (с защитой от брутфорса),
- CRUD списков и товаров,
- права доступа (владелец/участник, `read` / `write`),
- история покупок, пагинация, регистронезависимая дедупликация,
- статические и динамические рекомендации (включая регистр),
- автодополнение поиска,
- загрузка и удаление аватара,
- смена пароля и уникальность email/username/phone.

## ⚙️ CI/CD

GitHub Actions запускает `pytest` на каждый push в `master`.
Конфигурация: `.github/workflows/tests.yml`.

https://github.com/enderior/smart-shoplist-backend/actions/workflows/tests.yml/badge.svg

## 📁 Структура проекта

```text
smart-shoplist-backend/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # auth, users, lists, shared_lists,
│   │   │                        # recommendations, search, purchase_history
│   │   ├── core/                # config, database, security, dependencies,
│   │   │                        # email_validation
│   │   ├── data/                # associations.py (статические ассоциации)
│   │   ├── models/              # SQLAlchemy модели
│   │   ├── schemas/             # Pydantic схемы
│   │   ├── services/            # email.py
│   │   └── main.py              # точка входа FastAPI
│   ├── alembic/                 # миграции
│   ├── tests/                   # pytest-тесты
│   ├── static/avatars/          # пользовательские аватары (не в Git)
│   ├── .env                     # переменные окружения (не в Git)
│   ├── alembic.ini              # конфиг Alembic (URL берётся из .env)
│   ├── requirements.txt
│   └── run.py
├── .github/workflows/tests.yml  # CI
├── docs/database_schema.png     # схема БД
├── sql/                         # SQL-скрипты для ручной подготовки БД
├── .gitignore
└── README.md
```

## 📄 Лицензия

Проект разработан в учебных целях. Свободное использование.

---

Разработано в рамках учебного проекта.
Вопросы и предложения — в [issues](https://github.com/enderior/smart-shoplist-backend/issues).
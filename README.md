# Smart ShopList Backend

Бэкенд для умного списка покупок на FastAPI.

## Технологии

- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT аутентификация
- bcrypt (хеширование паролей)

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/enderior/smart-shoplist-backend.git
cd smart-shoplist-backend
```

### 2. Создание и активация виртуального окружения

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

### 3. Установка зависимостей

**Важно:** `asyncpg` требует готовый wheel-файл, поэтому используйте флаг `--only-binary`:

```bash
pip install -r requirements.txt --only-binary asyncpg
```

### 4. Настройка переменных окружения

Создайте файл `.env` в папке `backend/`:

```env
PROJECT_NAME="Smart ShopList API"
VERSION="1.0.0"
DEBUG=True

SECRET_KEY="your-secret-key-here"  # сгенерируйте через python -c "import secrets; print(secrets.token_urlsafe(32))"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smartlist

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smartlist
```

### 5. Настройка базы данных

Убедитесь, что PostgreSQL запущен, и создайте базу данных:

```sql
CREATE DATABASE smartlist;
```

Затем выполните скрипт для создания таблиц и тестовых данных:

```bash
psql -U postgres -d smartlist -f sql/full_schema.sql
```

### 6. Запуск сервера

```bash
python run.py
```

Сервер запустится на `http://localhost:8000`

Документация API: `http://localhost:8000/docs`

---

## API Эндпоинты

### Аутентификация

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/auth/register` | Регистрация нового пользователя |
| POST | `/auth/login` | Вход (возвращает JWT токен) |

### Пользователи

| Метод | Эндпоинт | Описание | Требует токен |
|-------|----------|----------|---------------|
| GET | `/users/` | Список всех пользователей | ❌ Нет |
| GET | `/users/{id}` | Получить пользователя по ID | ❌ Нет |
| GET | `/users/me` | Информация о текущем пользователе | ✅ Да |

### Списки покупок (в разработке)

| Метод | Эндпоинт | Описание | Требует токен |
|-------|----------|----------|---------------|
| GET | `/lists/` | Список всех списков пользователя | ✅ Да |
| POST | `/lists/` | Создать новый список | ✅ Да |
| GET | `/lists/{id}` | Получить список с элементами | ✅ Да |
| PUT | `/lists/{id}` | Обновить список | ✅ Да |
| DELETE | `/lists/{id}` | Удалить список | ✅ Да |
| POST | `/lists/{id}/items` | Добавить элемент в список | ✅ Да |
| PUT | `/items/{id}` | Обновить элемент | ✅ Да |
| DELETE | `/items/{id}` | Удалить элемент | ✅ Да |

---

## Примеры запросов

### Регистрация

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "username",
    "password": "password123",
    "phone": "+79123456789"
  }'
```

### Логин

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Получение данных текущего пользователя

```bash
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer <your_access_token>"
```

---

## Схема базы данных

![Database Schema](docs/database_schema.png)

### Таблицы

- **users** — пользователи (id, email, username, phone, hashed_password, is_active, created_at, updated_at)
- **shopping_lists** — списки покупок (id, title, description, owner_id, is_archived, created_at, updated_at)
- **list_items** — элементы списков (id, list_id, name, quantity, unit, is_completed, position, created_at)

### Связи

- `shopping_lists.owner_id` → `users.id` (один пользователь может иметь много списков)
- `list_items.list_id` → `shopping_lists.id` (один список может содержать много элементов)

---

## SQL-скрипты

В папке `sql/` находятся:

| Файл | Описание |
|------|----------|
| `full_schema.sql` | Полная схема БД + тестовые данные |
| `02_seed.sql` | Только тестовые данные |
| `03_queries.sql` | Примеры SQL-запросов (JOIN, GROUP BY, агрегации) |

---

## Структура проекта

```
smart-shoplist/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # API эндпоинты
│   │   ├── core/               # Конфигурация, БД, безопасность
│   │   ├── models/             # SQLAlchemy модели
│   │   └── schemas/            # Pydantic схемы
│   ├── .env                    # Переменные окружения
│   ├── requirements.txt        # Зависимости
│   └── run.py                  # Точка входа
├── docs/
│   └── database_schema.png     # Схема БД
├── sql/                        # SQL-скрипты
└── README.md
```
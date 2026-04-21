# Smart ShopList Backend

Бэкенд для «умного» списка покупок на **FastAPI**.  
Поддерживает JWT-аутентификацию, управление списками и товарами, историю покупок, а также базовые «умные» рекомендации (на основе статического словаря и истории пользователя).

[![Run tests](https://github.com/enderior/smart-shoplist-backend/actions/workflows/tests.yml/badge.svg)](https://github.com/enderior/smart-shoplist-backend/actions/workflows/tests.yml)

## 📋 Содержание

- [Технологии](#технологии)
- [Установка и запуск](#установка-и-запуск)
- [API Эндпоинты](#api-эндпоинты)
- [Схема базы данных](#схема-базы-данных)
- [Тестирование](#тестирование)
- [CI/CD](#cicd)
- [Структура проекта](#структура-проекта)

## 🛠 Технологии

- **FastAPI** – веб-фреймворк
- **SQLAlchemy 2.0** – асинхронная ORM
- **PostgreSQL** – база данных
- **Alembic** – миграции
- **Pydantic** – валидация данных
- **python-jose** – JWT токены
- **bcrypt** – хеширование паролей
- **pytest** – тестирование
- **GitHub Actions** – CI/CD

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/enderior/smart-shoplist-backend.git
cd smart-shoplist-backend
```

### 2. Настройка виртуального окружения и зависимостей

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt --only-binary asyncpg
```

### 3. Настройка переменных окружения

Скопируй `.env.example` в `.env` (или создай вручную). Минимальный пример:

```env
PROJECT_NAME="Smart ShopList API"
VERSION="1.0.0"
DEBUG=True

SECRET_KEY="your-secret-key-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smartlist

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smartlist
```

### 4. Подготовка базы данных (PostgreSQL)

Убедись, что PostgreSQL запущен. Создай базу данных:

```sql
CREATE DATABASE smartlist WITH ENCODING='UTF8' LC_COLLATE='Russian_Russia.1251' LC_CTYPE='Russian_Russia.1251' TEMPLATE=template0;
```

Примени миграции Alembic:

```bash
alembic upgrade head
```

(Опционально) Заполни тестовыми данными:

```bash
psql -U postgres -d smartlist -f sql/full_schema.sql   # или только часть с INSERT
```

### 5. Запуск сервера

```bash
python run.py
```

Сервер будет доступен по адресу `http://localhost:8000`.  
Документация Swagger: `http://localhost:8000/docs`

## 📡 API Эндпоинты

### Аутентификация

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/auth/register` | Регистрация пользователя |
| POST | `/auth/login` | Вход (возвращает JWT токен) |

### Пользователи

| Метод | Эндпоинт | Описание | Требует токен |
|-------|----------|----------|---------------|
| GET | `/users/me` | Информация о текущем пользователе | ✅ |
| GET | `/users/` | Список всех пользователей | ❌ |
| GET | `/users/{id}` | Получить пользователя по ID | ❌ |

### Списки покупок

| Метод | Эндпоинт | Описание | Требует токен |
|-------|----------|----------|---------------|
| POST | `/lists/` | Создать новый список | ✅ |
| GET | `/lists/` | Все списки текущего пользователя | ✅ |
| GET | `/lists/{id}` | Получить список с товарами | ✅ |
| PUT | `/lists/{id}` | Обновить список (название, описание) | ✅ |
| DELETE | `/lists/{id}` | Удалить список (каскадно) | ✅ |

### Товары (элементы списка)

| Метод | Эндпоинт | Описание | Требует токен |
|-------|----------|----------|---------------|
| POST | `/lists/{list_id}/items` | Добавить товар в список | ✅ |
| PUT | `/items/{item_id}` | Обновить товар (кол-во, отметка о покупке) | ✅ |
| DELETE | `/items/{item_id}` | Удалить товар из списка | ✅ |

### История покупок и рекомендации

| Метод | Эндпоинт | Описание | Требует токен |
|-------|----------|----------|---------------|
| GET | `/purchase-history/` | История покупок пользователя (поддерживает `skip`/`limit`) | ✅ |
| GET | `/recommendations/{product_name}` | Рекомендации (статический словарь + анализ истории) | ✅ |

## 🗄 Схема базы данных

![Схема БД](docs/database_schema.png)

*Диаграмма создана с помощью [dbdiagram.io](https://dbdiagram.io).*

### Описание таблиц

- **users** – пользователи (id, email, username, phone, hashed_password, is_active, created_at, updated_at, birth_date, avatar_url)
- **shopping_lists** – списки покупок (id, title, description, owner_id, is_archived, created_at, updated_at)
- **list_items** – товары в списках (id, list_id, name, quantity, unit, is_completed, position, created_at)
- **purchase_history** – история покупок (id, user_id, product_name, purchased_at)

### Связи

- `shopping_lists.owner_id` → `users.id` (один пользователь может иметь много списков)
- `list_items.list_id` → `shopping_lists.id` (один список может содержать много товаров)
- `purchase_history.user_id` → `users.id` (история принадлежит пользователю)

## 🧪 Тестирование

Для запуска тестов используется `pytest` с отдельной тестовой БД (SQLite).

```bash
cd backend
pytest -v
```

Тесты покрывают:
- регистрацию и логин,
- создание, обновление и удаление списков,
- добавление, обновление и удаление товаров,
- права доступа (чужие списки/товары),
- историю покупок и пагинацию,
- статические и динамические рекомендации.

## ⚙️ CI/CD

Проект использует **GitHub Actions** для автоматического запуска тестов при каждом push в ветку `master`.  
Файл конфигурации: `.github/workflows/tests.yml`.

Статус последнего запуска: [![Run tests](https://github.com/enderior/smart-shoplist-backend/actions/workflows/tests.yml/badge.svg)](https://github.com/enderior/smart-shoplist-backend/actions/workflows/tests.yml)

## 📁 Структура проекта

```
smart-shoplist/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # Эндпоинты (auth, users, lists, recommendations, purchase_history)
│   │   ├── core/               # Конфигурация, БД, безопасность
│   │   ├── models/             # SQLAlchemy модели
│   │   ├── schemas/            # Pydantic схемы
│   │   └── main.py             # Точка входа FastAPI
│   ├── alembic/                # Миграции БД
│   ├── tests/                  # Модульные тесты
│   ├── .env                    # Переменные окружения (не в Git)
│   ├── requirements.txt        # Зависимости
│   └── run.py                  # Запуск сервера
├── .github/workflows/          # CI/CD конфигурация
├── docs/
│   └── database_schema.png     # Диаграмма БД
├── sql/                        # SQL-скрипты (инициализация, тестовые данные)
├── .gitignore
└── README.md
```

## 📄 Лицензия

Проект разработан в учебных целях. Свободное использование.

---

**Разработано в рамках учебного проекта.**  
По всем вопросам обращайтесь в [Issues](https://github.com/enderior/smart-shoplist-backend/issues).

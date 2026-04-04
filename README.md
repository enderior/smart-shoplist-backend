# Smart ShopList Backend

Бэкенд для умного списка покупок на FastAPI.

## Технологии

- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT аутентификация

## Запуск

```bash
cd backend
python -m pip install -r requirements.txt --only-binary asyncpg
python run.py
```

## Схема базы данных

![Database Schema](docs/database_schema.png)

### Таблицы

- **users** — пользователи (id, email, username, phone, hashed_password, is_active, created_at, updated_at)
- **shopping_lists** — списки покупок (id, title, description, owner_id, is_archived, created_at, updated_at)
- **list_items** — элементы списков (id, list_id, name, quantity, unit, is_completed, position, created_at)

### Связи

- `shopping_lists.owner_id` → `users.id` (один пользователь может иметь много списков)
- `list_items.list_id` → `shopping_lists.id` (один список может содержать много элементов)
"""
Заполнение БД тестовыми данными.

Использование:
    cd backend
    python scripts/seed_data.py           # добавить, если пользователей нет
    python scripts/seed_data.py --reset   # удалить seed-юзеров и создать заново
"""
import asyncio
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    User, ShoppingList, ListItem, ListMember,
    PurchaseHistory, SearchHistory, Product,
    PasswordResetToken, ContactChangeToken,
)

# ============ Данные ============

USERS = [
    {"email": "alice@example.com", "username": "alice", "password": "alice123", "phone": "+79001110001"},
    {"email": "bob@example.com", "username": "bob", "password": "bob12345", "phone": "+79001110002"},
    {"email": "carol@example.com", "username": "carol", "password": "carol123", "phone": "+79001110003"},
]

# Списки по пользователю: (название, [(товар, кол-во, ед.)])
LISTS = {
    "alice": [
        ("Продукты на неделю", [
            ("Хлеб", 1, "шт"), ("Молоко", 2, "л"), ("Яйца", 10, "шт"),
            ("Масло сливочное", 1, "шт"), ("Сыр", 300, "г"),
            ("Курица", 1, "кг"), ("Картофель", 2, "кг"),
        ]),
        ("Завтрак", [
            ("Овсянка", 1, "уп"), ("Молоко", 1, "л"), ("Мёд", 1, "шт"),
            ("Хлеб", 1, "шт"), ("Творог", 200, "г"),
        ]),
        ("Для пикника", [
            ("Колбаски", 500, "г"), ("Хлеб", 1, "шт"), ("Кетчуп", 1, "шт"),
            ("Огурцы", 500, "г"), ("Помидоры", 500, "г"),
            ("Уголь", 1, "уп"), ("Сок", 2, "л"),
        ]),
        ("Для выпечки", [
            ("Мука", 1, "кг"), ("Сахар", 1, "кг"), ("Яйца", 10, "шт"),
            ("Масло сливочное", 200, "г"), ("Разрыхлитель", 1, "уп"),
            ("Ванилин", 1, "уп"),
        ]),
        ("Ужин на двоих", [
            ("Стейк", 2, "шт"), ("Вино", 1, "бут"), ("Картофель", 500, "г"),
            ("Салат", 1, "уп"), ("Помидоры черри", 200, "г"),
        ]),
        ("Хозтовары", [
            ("Мыло", 1, "шт"), ("Зубная паста", 1, "шт"),
            ("Стиральный порошок", 1, "уп"), ("Салфетки", 2, "уп"),
        ]),
    ],
    "bob": [
        ("На неделю", [
            ("Рис", 1, "кг"), ("Макароны", 500, "г"), ("Курица", 1, "кг"),
            ("Помидоры", 300, "г"), ("Сметана", 200, "г"), ("Хлеб", 1, "шт"),
        ]),
        ("Спортпит", [
            ("Протеин", 1, "уп"), ("Батончики", 6, "шт"),
            ("Бананы", 1, "кг"), ("Творог", 400, "г"), ("Яйца", 20, "шт"),
        ]),
        ("Для гостей", [
            ("Чипсы", 3, "уп"), ("Пиво", 6, "бут"), ("Колбаски", 300, "г"),
            ("Сыр", 200, "г"), ("Орехи", 200, "г"),
        ]),
        ("Завтрак", [
            ("Кофе", 1, "уп"), ("Молоко", 1, "л"),
            ("Круассаны", 4, "шт"), ("Масло сливочное", 1, "шт"),
        ]),
        ("Итальянский вечер", [
            ("Спагетти", 500, "г"), ("Томатный соус", 1, "шт"),
            ("Пармезан", 200, "г"), ("Базилик", 1, "уп"), ("Вино", 1, "бут"),
        ]),
        ("Пятничный ужин", [
            ("Пицца", 1, "шт"), ("Кола", 2, "л"), ("Мороженое", 1, "шт"),
        ]),
    ],
    "carol": [
        ("Основное", [
            ("Гречка", 1, "кг"), ("Молоко", 2, "л"), ("Йогурт", 4, "шт"),
            ("Хлеб", 2, "шт"), ("Сыр", 300, "г"), ("Яйца", 10, "шт"),
        ]),
        ("Овощи и фрукты", [
            ("Яблоки", 1, "кг"), ("Бананы", 1, "кг"), ("Апельсины", 1, "кг"),
            ("Огурцы", 500, "г"), ("Помидоры", 500, "г"), ("Морковь", 1, "кг"),
        ]),
        ("Детское", [
            ("Каша детская", 3, "уп"), ("Пюре фруктовое", 5, "шт"),
            ("Печенье детское", 2, "уп"), ("Сок детский", 3, "шт"),
        ]),
        ("Уборка", [
            ("Моющее средство", 1, "шт"), ("Губки", 4, "шт"),
            ("Мешки для мусора", 2, "уп"),
        ]),
        ("Праздничный стол", [
            ("Шампанское", 2, "бут"), ("Красная икра", 1, "шт"),
            ("Сырная тарелка", 1, "уп"), ("Виноград", 1, "кг"),
            ("Шоколад", 3, "шт"), ("Мандарины", 2, "кг"),
        ]),
        ("На дачу", [
            ("Шашлык маринованный", 2, "кг"), ("Уголь", 2, "уп"),
            ("Одноразовая посуда", 1, "уп"), ("Вода", 5, "бут"),
            ("Хлеб", 2, "шт"),
        ]),
    ],
}

# Что юзер уже "купил" (для purchase_history и рекомендаций)
PURCHASES = {
    "alice": [
        "Хлеб", "Молоко", "Яйца", "Масло сливочное", "Сыр", "Курица",
        "Картофель", "Помидоры", "Кетчуп", "Колбаски", "Мука", "Сахар",
    ],
    "bob": [
        "Рис", "Макароны", "Курица", "Помидоры", "Сметана", "Хлеб",
        "Кофе", "Молоко", "Спагетти", "Томатный соус", "Пармезан",
    ],
    "carol": [
        "Гречка", "Молоко", "Йогурт", "Хлеб", "Сыр", "Яйца",
        "Яблоки", "Бананы", "Шампанское", "Шоколад", "Мандарины",
    ],
}

# Совместные списки
SHARED_LISTS = [
    {
        "owner": "alice", "guest": "bob", "permission": "write",
        "title": "Новый год",
        "items": [
            ("Шампанское", 2, "бут"), ("Мандарины", 2, "кг"),
            ("Оливье", 1, "уп"), ("Свечи", 1, "уп"),
            ("Подарочная бумага", 1, "уп"),
        ],
    },
    {
        "owner": "bob", "guest": "carol", "permission": "read",
        "title": "Пикник в субботу",
        "items": [
            ("Шашлык", 2, "кг"), ("Овощи гриль", 1, "уп"),
            ("Соус барбекю", 1, "шт"), ("Напитки", 4, "бут"),
        ],
    },
]


# ============ Логика ============

def _collect_all_products() -> dict:
    """Возвращает {normalized_name: display_name} по всем источникам."""
    products = {}

    def add(name: str):
        norm = name.strip().lower()
        products.setdefault(norm, name)

    for items in LISTS.values():
        for _, item_list in items:
            for name, _, _ in item_list:
                add(name)

    for items in PURCHASES.values():
        for name in items:
            add(name)

    for s in SHARED_LISTS:
        for name, _, _ in s["items"]:
            add(name)

    return products


async def reset_seed_users(db, emails) -> int:
    users = (await db.execute(select(User).where(User.email.in_(emails)))).scalars().all()
    if not users:
        return 0
    user_ids = [u.id for u in users]

    list_ids = (await db.execute(
        select(ShoppingList.id).where(ShoppingList.owner_id.in_(user_ids))
    )).scalars().all()

    if list_ids:
        await db.execute(delete(ListMember).where(
            ListMember.user_id.in_(user_ids) | ListMember.list_id.in_(list_ids)
        ))
        await db.execute(delete(ListItem).where(ListItem.list_id.in_(list_ids)))
        await db.execute(delete(ShoppingList).where(ShoppingList.id.in_(list_ids)))
    else:
        await db.execute(delete(ListMember).where(ListMember.user_id.in_(user_ids)))

    await db.execute(delete(PurchaseHistory).where(PurchaseHistory.user_id.in_(user_ids)))
    await db.execute(delete(SearchHistory).where(SearchHistory.user_id.in_(user_ids)))
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id.in_(user_ids)))
    await db.execute(delete(ContactChangeToken).where(ContactChangeToken.user_id.in_(user_ids)))
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()
    return len(user_ids)


async def seed(reset: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        if reset:
            emails = [u["email"] for u in USERS]
            removed = await reset_seed_users(db, emails)
            print(f"🗑  Удалено seed-пользователей: {removed}")

        existing = (await db.execute(
            select(User.email).where(User.email.in_([u["email"] for u in USERS]))
        )).scalars().all()
        if existing:
            print(f"⚠️  Уже существуют пользователи: {existing}")
            print("    Запусти с флагом --reset, чтобы пересоздать.")
            return

        # 1. Users
        users_by_username = {}
        for u in USERS:
            user = User(
                email=u["email"],
                username=u["username"],
                hashed_password=get_password_hash(u["password"]),
                phone=u.get("phone"),
            )
            db.add(user)
            users_by_username[u["username"]] = user
        await db.commit()
        for user in users_by_username.values():
            await db.refresh(user)
        print(f"👤 Пользователей: {len(users_by_username)}")

        # 2. Личные списки + товары
        list_count = item_count = 0
        seen_sh = {}  # user_id -> set of normalized names
        for username, user in users_by_username.items():
            seen_sh[user.id] = set()

            for title, items in LISTS[username]:
                sl = ShoppingList(title=title, owner_id=user.id)
                db.add(sl)
                await db.commit()
                await db.refresh(sl)
                list_count += 1

                for name, qty, unit in items:
                    db.add(ListItem(
                        list_id=sl.id, name=name,
                        quantity=qty, unit=unit, is_completed=False,
                    ))
                    item_count += 1

                    norm = name.strip().lower()
                    if norm not in seen_sh[user.id]:
                        seen_sh[user.id].add(norm)
                        db.add(SearchHistory(user_id=user.id, product_name=name))
                await db.commit()

        print(f"📋 Личных списков: {list_count}")
        print(f"🛒 Товаров в личных списках: {item_count}")

        # 3. purchase_history
        ph_count = 0
        seen_ph = {}
        for username, user in users_by_username.items():
            seen_ph[user.id] = set()
            for name in PURCHASES[username]:
                norm = name.strip().lower()
                if norm in seen_ph[user.id]:
                    continue
                seen_ph[user.id].add(norm)
                db.add(PurchaseHistory(user_id=user.id, product_name=name))
                ph_count += 1
        await db.commit()
        print(f"📜 purchase_history: {ph_count}")

        # 4. products — общий справочник
        all_products = _collect_all_products()
        added = 0
        for norm, name in all_products.items():
            existing_p = (await db.execute(
                select(Product).where(Product.normalized_name == norm)
            )).scalar_one_or_none()
            if not existing_p:
                db.add(Product(name=name, normalized_name=norm))
                added += 1
        await db.commit()
        print(f"📦 products: {len(all_products)} (новых: {added})")

        # 5. Совместные списки
        shared_count = 0
        for s in SHARED_LISTS:
            owner = users_by_username[s["owner"]]
            guest = users_by_username[s["guest"]]

            sl = ShoppingList(title=s["title"], owner_id=owner.id)
            db.add(sl)
            await db.commit()
            await db.refresh(sl)
            shared_count += 1

            for name, qty, unit in s["items"]:
                db.add(ListItem(
                    list_id=sl.id, name=name,
                    quantity=qty, unit=unit, is_completed=False,
                ))
                # history уже добавлена у владельца, если надо
                await db.commit()

            db.add(ListMember(
                list_id=sl.id, user_id=guest.id,
                permission=s["permission"],
            ))
            await db.commit()

        print(f"🤝 Совместных списков: {shared_count}")

        # 6. Сводка
        print()
        print("=" * 55)
        print("✅ Готово! Логины (email / password):")
        for u in USERS:
            print(f"   {u['email']:26s} / {u['password']}")
        print("=" * 55)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed test data")
    parser.add_argument("--reset", action="store_true",
                        help="Удалить seed-юзеров и создать заново")
    args = parser.parse_args()
    asyncio.run(seed(reset=args.reset))


if __name__ == "__main__":
    main()

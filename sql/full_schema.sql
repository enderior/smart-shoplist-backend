-- ============================================
-- Smart ShopList - Полная схема базы данных
-- ============================================

-- ============================================
-- 1. Создание таблиц
-- ============================================

-- Таблица пользователей
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Таблица списков покупок
CREATE TABLE shopping_lists (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Таблица элементов списка
CREATE TABLE list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit VARCHAR(20),
    is_completed BOOLEAN DEFAULT false,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- ============================================
-- 2. Индексы
-- ============================================
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_shopping_lists_owner_id ON shopping_lists(owner_id);
CREATE INDEX idx_list_items_list_id ON list_items(list_id);

-- ============================================
-- 3. Тестовые данные
-- ============================================

-- Пользователи
INSERT INTO users (email, username, phone, hashed_password) VALUES
('john@example.com', 'john_doe', '+79123456789', 'hash1'),
('mary@example.com', 'mary_smith', '+79876543210', 'hash2');

-- Списки покупок
INSERT INTO shopping_lists (title, description, owner_id) VALUES
('Продукты на неделю', 'Основные продукты', 1),
('Для пикника', 'Еда на природу', 1),
('Подарки', NULL, 2);

-- Элементы списков
INSERT INTO list_items (list_id, name, quantity, unit, is_completed, position) VALUES
(1, 'Молоко', 2, 'л', false, 0),
(1, 'Хлеб', 1, 'шт', true, 1),
(1, 'Яйца', 10, 'шт', false, 2),
(2, 'Колбаски', 500, 'г', false, 0),
(2, 'Хлеб', 1, 'шт', false, 1),
(2, 'Кетчуп', 1, 'шт', false, 2),
(3, 'Книга', 1, 'шт', false, 0);
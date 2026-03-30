-- ============================================
-- Тестовые данные для Smart ShopList
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
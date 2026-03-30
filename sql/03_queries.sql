-- ============================================
-- Примеры SQL-запросов для Smart ShopList
-- ============================================

-- 1. Все пользователи
SELECT * FROM users;

-- 2. Все списки с именами владельцев
SELECT
    sl.id,
    sl.title,
    u.username AS owner_name
FROM shopping_lists sl
JOIN users u ON sl.owner_id = u.id;

-- 3. Полный список с элементами
SELECT
    sl.title AS list_name,
    li.name AS product,
    li.quantity,
    li.unit,
    CASE WHEN li.is_completed THEN '✓' ELSE '□' END AS status
FROM shopping_lists sl
LEFT JOIN list_items li ON sl.id = li.list_id
ORDER BY sl.id, li.position;

-- 4. Количество элементов в каждом списке
SELECT
    sl.title,
    COUNT(li.id) AS items_count
FROM shopping_lists sl
LEFT JOIN list_items li ON sl.id = li.list_id
GROUP BY sl.id, sl.title;

-- 5. Незавершённые элементы для списка №1
SELECT * FROM list_items
WHERE list_id = 1 AND is_completed = false
ORDER BY position;

-- 6. Продукты, которые нужно купить (по всем спискам)
SELECT
    li.name,
    SUM(li.quantity) AS total_quantity,
    li.unit
FROM list_items li
WHERE li.is_completed = false
GROUP BY li.name, li.unit
ORDER BY total_quantity DESC;

-- 7. Отметить продукт как купленный (пример UPDATE)
-- UPDATE list_items SET is_completed = true WHERE id = 1;

-- 8. Добавить новый список (пример INSERT)
-- INSERT INTO shopping_lists (title, owner_id) VALUES ('Новый список', 1);

-- 9. Удалить выполненный элемент (пример DELETE)
-- DELETE FROM list_items WHERE id = 1;
-- ============================================================
-- Дедупликация purchase_history перед навешиванием UNIQUE
-- ============================================================
-- Нужен, если alembic upgrade падает с ошибкой:
--   DETAIL: Ключ (user_id, product_name)=(...) дублируется.
--
-- Запускать в pgAdmin → Query Tool для базы smartlist.
-- ============================================================

BEGIN;

-- 1. Диагностика (закомментируй, если не нужно)
-- SELECT user_id, product_name, COUNT(*) FROM purchase_history
-- GROUP BY user_id, product_name HAVING COUNT(*) > 1;

-- 2. Удаляем всё, кроме самой свежей записи
--    на (user_id, LOWER(TRIM(product_name)))
DELETE FROM purchase_history
WHERE id NOT IN (
    SELECT DISTINCT ON (user_id, LOWER(TRIM(product_name))) id
    FROM purchase_history
    ORDER BY user_id, LOWER(TRIM(product_name)), purchased_at DESC
);

-- 3. Опционально: нормализуем имя, чтобы регистр не «прыгал»
--    (раскомментируй, если хочешь единообразие)
-- UPDATE purchase_history SET product_name = LOWER(TRIM(product_name));

COMMIT;
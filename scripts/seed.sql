-- Очистка таблиц перед вставкой
DELETE FROM meeting_history;
DELETE FROM calls;
DELETE FROM meetings;
DELETE FROM companies;
DELETE FROM managers;

-- 1. Менеджеры
INSERT INTO managers (id, name, email, phone, is_active, created_at) VALUES 
(1, 'Иван Иванов', 'ivan@example.com', '+77770000001', 1, '2026-11-16 09:00:00'),
(2, 'Анна Смирнова', 'anna@example.com', '+77770000002', 1, '2026-11-16 09:00:00'),
(3, 'Олег Петров', 'oleg@example.com', '+77770000003', 1, '2026-11-16 09:00:00');

-- 2. Организации (клиенты)
INSERT INTO companies (id, name, bin, phone, status, created_at) VALUES 
(1, 'ТОО "Альфа"', '123456789012', '+77011112233', 'new', '2026-11-16 09:00:00'),
(2, 'ТОО "Бета"', '987654321098', '+77022223344', 'in_progress', '2026-11-16 09:00:00'),
(3, 'АО "Гамма"', '112233445566', '+77033334455', 'meeting_set', '2026-11-16 09:00:00'),
(4, 'ИП "Дельта"', '998877665544', '+77044445566', 'new', '2026-11-16 09:00:00');

-- 3. Звонки
INSERT INTO calls (id, company_id, manager_id, result, called_at, note) VALUES 
(1, 1, 1, 'no_answer', '2026-11-17 10:00:00', 'Не взял трубку'),
(2, 2, 2, 'refused', '2026-11-17 11:30:00', 'Сказали не интересно'),
(3, 3, 1, 'meeting_set', '2026-11-17 14:00:00', 'Договорились на среду');

-- 4. Встречи (время в UTC!)
INSERT INTO meetings (id, company_id, manager_id, scheduled_at, duration_minutes, status, original_scheduled_at, created_at, updated_at) VALUES 
(1, 3, 1, '2026-11-18 05:00:00', 60, 'scheduled', '2026-11-18 05:00:00', '2026-11-17 14:00:00', '2026-11-17 14:00:00');

-- 5. История встречи
INSERT INTO meeting_history (meeting_id, action, new_scheduled_at, changed_at, note) VALUES 
(1, 'created', '2026-11-18 05:00:00', '2026-11-17 14:00:00', 'Первоначальное назначение');

-- 6. Обновляем звонок
UPDATE calls SET meeting_id = 1 WHERE id = 3;
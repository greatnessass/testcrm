-- Схема базы данных CRM (SQLite).
-- Можно применить вручную: sqlite3 crm.db < migrations/init.sql
-- Также таблицы создаются автоматически при старте приложения (init_db).

PRAGMA foreign_keys = ON;

-- Менеджеры отдела обзвона
CREATE TABLE IF NOT EXISTS managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Организации (заказчики)
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bin TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Звонки (результаты обзвона)
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    manager_id INTEGER NOT NULL REFERENCES managers(id),
    result TEXT NOT NULL CHECK (result IN ('no_answer', 'refused', 'meeting_set')),
    meeting_id INTEGER REFERENCES meetings(id),
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT
);

-- Встречи с менеджерами
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    manager_id INTEGER NOT NULL REFERENCES managers(id),
    scheduled_at TIMESTAMP NOT NULL,   -- UTC
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    status TEXT NOT NULL DEFAULT 'scheduled',
    original_scheduled_at TIMESTAMP,   -- UTC — время первой записи встречи
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- История изменений встреч (переносы, отмены)
CREATE TABLE IF NOT EXISTS meeting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    action TEXT NOT NULL,                 -- created | rescheduled | cancelled
    previous_scheduled_at TIMESTAMP,      -- UTC
    new_scheduled_at TIMESTAMP,           -- UTC
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT
);

-- Индексы для ускорения выборок по времени и менеджеру/организации
CREATE INDEX IF NOT EXISTS idx_meetings_manager_status ON meetings(manager_id, status);
CREATE INDEX IF NOT EXISTS idx_meetings_company_status ON meetings(company_id, status);
CREATE INDEX IF NOT EXISTS idx_meetings_scheduled_at ON meetings(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_calls_meeting_id ON calls(meeting_id);
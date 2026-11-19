# CRM API — отдел обзвона (Задание Б)

REST API для внутренней CRM отдела обзвона. Только бэкенд, без интерфейса.

## Стек

- Python 3.10+
- FastAPI — веб-фреймворк
- SQLAlchemy 2.0 — ORM
- SQLite — база данных (файл `crm.db`)
- Pydantic v2 — валидация данных
- pytest — тесты
- zoneinfo (встроенная) — часовые пояса (Asia/Almaty = UTC+5)

Доп. зависимости только для тестов: `httpx` (TestClient).

## Структура проекта

```
crm_api/
├── app/
│   ├── __init__.py
│   ├── config.py        # настройки (pydantic-settings)
│   ├── database.py      # движок, сессии, init_db
│   ├── models.py        # SQLAlchemy-модели
│   ├── schemas.py       # Pydantic-схемы
│   ├── exceptions.py    # кастомные исключения (HTTPException-потомки)
│   ├── services.py      # бизнес-логика (вся здесь)
│   ├── routes.py        # HTTP-роутеры
│   └── main.py          # FastAPI приложение
├── migrations/
│   └── init.sql         # canonical схема (также создаётся через create_all)
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # фикстура клиента, тестовая БД
│   ├── test_companies.py
│   ├── test_calls.py
│   ├── test_meetings.py
│   └── test_schedule.py
├── scripts/
│   └── examples.http    # примеры запросов
├── README.md
├── REFLECTION.md
├── EXPLAIN.md
├── requirements.txt
└── .gitignore
```

## Запуск с нуля (одна команда)

### 1. Установить зависимости

```powershell
# создать и активировать виртуальное окружение
python -m venv venv
.\venv\Scripts\Activate.ps1

# установить зависимости
pip install -r requirements.txt
```

### 2. Запустить сервер

```powershell
uvicorn app.main:app --reload
```

База инициализируется автоматически при старте (событие `startup` вызывает `init_db()` → `Base.metadata.create_all`).  
API будет доступно по адресу: `http://localhost:8000`  
Документация Swagger: `http://localhost:8000/docs`

### 3. Примеры запросов

См. `scripts/examples.http` (можно открыть в VS Code с расширением REST Client или выполнить через curl).
См. `scripts/test.http`

Пример через curl:
```powershell
curl -X POST http://localhost:8000/companies ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"ТОО Альфа\",\"bin\":\"1234567890123\",\"phone\":\"+77777777777\"}"
```

## Запуск тестов

```powershell
pytest -v
```

Или с отчётом о покрытии (если установлен pytest-cov):
```powershell
pytest -v --cov=app
```

Все тесты используют временный файл SQLite, основная база `crm.db` не затрагивается.

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./crm.db` | URL базы данных SQLite |

## Ручное тестирование (Swagger / REST Client)

Для быстрой проверки работы API с реальными данными в репозитории есть скрипты:

### 1. Заполнение базы тестовыми данными (Seed)

В корне проекта лежит скрипт `seed.py`. Он заполняет базу тестовыми менеджерами, компаниями, звонками и встречей.

**Как запустить:**
1. Убедитесь, что база создана (запустите сервер на пару секунд и остановите, либо просто выполните `python -c "from app.database import init_db; init_db()"`).
2. Выполните в терминале:
   ```bash
   python .\scripts\seed.py

## Что реализовано (по ТЗ)

- ✅ POST /companies — создать организацию (название, БИН, телефон)
- ✅ GET /companies?status= — список с фильтром по статусу и пагинацией
- ✅ POST /calls — результат звонка (no_answer / refused / meeting_set)
- ✅ POST /meetings — назначить встречу менеджеру
- ✅ PATCH /meetings/{id} — перенести или отменить встречу
- ✅ GET /managers/{id}/schedule?date= — расписание менеджера на день
- ✅ Время в API — UTC (ISO 8601); бизнес-проверки — в Asia/Almaty (UTC+5)
- ✅ Длительность встречи — ровно 60 минут
- ✅ Рабочие часы: пн–пт, 09:00–18:00 по Алматы; встреча должна укладываться целиком
- ✅ Нет пересекающихся встреч у менеджера (смежные слоты разрешены)
- ✅ Нет двух активных встреч у одной организации одновременно (даже с разными менеджерами)
- ✅ meeting_set без meeting_id — ошибка валидации
- ✅ Перенос встречи сохраняет `original_scheduled_at` и историю (`meeting_history`)
- ✅ Корректные HTTP-коды: 200, 201, 400, 404, 409, 422 + JSON-сообщение об ошибке
- ✅ Минимум 5 автотестов (всего 17): компании, звонки, встречи, расписание
- ✅ Тесты на пересечение встреч и границы рабочего дня (17:30 отказ, 17:00 успех, 08:30 отказ)

## Что не реализовано (умышленно, по ТЗ)

- ❌ Авторизация и роли
- ❌ Очереди задач
- ❌ Уведомления (email/SMS)
- ❌ Кэширование
- ❌ Alembic-миграции (схема через `init.sql` + `create_all` — разрешено ТЗ)
- ❌ Docker (запуск через uvicorn одной командой)

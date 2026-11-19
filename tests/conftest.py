"""Конфигурация тестов.

Перед импортом любого модуля приложения устанавливается переменная DATABASE_URL
на временный файл SQLite, чтобы тесты не трогали основную базу crm.db.
Каждый тест получает чистую базу (drop_all/create_all).
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# --- Важно: задать тестовую БД ДО импорта app-модулей ---
_temp_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_temp_dir}/test.db"

from app.main import app
from app.database import engine, init_db
from app import models


@pytest.fixture(scope="function")
def client():
    """Тестовый клиент FastAPI с чистой базой для каждого теста."""
    models.Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as c:
        yield c

"""Инициализация базы данных.

Создаёт движок SQLAlchemy и сессии для работы с БД.
Для SQLite используется sqlite3 с поддержкой foreign keys.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Создаём движок. check_same_thread=False нужно, чтобы сессии можно было
# использовать из разных потоков (например, в тестах с TestClient).
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Фабрика сессий: каждый запрос берёт сессию, использует и закрывает.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс, от которого наследуются все модели.
Base = declarative_base()


def get_db():
    """Генератор сессии для FastAPI dependency injection.

    Каждый вызов роутера получает свежую сессию, которая автоматически
    закрывается после обработки запроса (even при исключениях).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создаёт все таблицы в БД на основе моделей.

    Вызывается один раз при старте приложения (например, через init_db.py).
    """
    Base.metadata.create_all(bind=engine)
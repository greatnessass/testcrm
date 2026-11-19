"""Конфигурация приложения.

Все настройки берутся из переменных окружения или значений по умолчанию.
Используем pydantic-settings для валидации конфигурации.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения.

    Атрибуты:
        database_url: URL SQLite-базы данных (относительный путь или абсолютный).
        almaty_tz: строковое представление часового пояса Asia/Almaty (UTC+5).
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    database_url: str = "sqlite:///./crm.db"
    almaty_tz: str = "Asia/Almaty"


settings = Settings()
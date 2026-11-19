"""FastAPI-приложение CRM."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.database import init_db
from app import routes


app = FastAPI(title="CRM API", version="1.0.0")


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc: IntegrityError):
    """Сеть безопасности: любая ошибка целостности БД (уникальность, FK) возвращает 409, а не 500."""
    return JSONResponse(
        status_code=409,
        content={"detail": "Конфликт данных: нарушение ограничения уникальности или связей в базе данных."},
    )


@app.on_event("startup")
def startup():
    """Создаёт таблицы при старте приложения."""
    init_db()


app.include_router(routes.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Исключения CRM (HTTPException-потомки) обрабатываются FastAPI по умолчанию,
# возвращая JSON {"detail": <message>} с нужным статусом.
# Проверки Pydantic (RequestValidationError) возвращают стандартный ответ FastAPI.
"""Кастомные исключения CRM.

Все наследуются от HTTPException, поэтому FastAPI автоматически возвращает
JSON-ответ с полем detail и соответствующим HTTP-статусом.
"""

from fastapi import HTTPException, status


class CRMError(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code=status_code, detail=message)


class MeetingConflictError(CRMError):
    def __init__(self, message: str = "Встреча пересекается с существующей встречей."):
        super().__init__(status_code=status.HTTP_409_CONFLICT, message=message)


class OutsideWorkingHoursError(CRMError):
    def __init__(self, message: str = "Время встречи выходит за пределы рабочего дня."):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message)


class NotFoundError(CRMError):
    def __init__(self, message: str = "Объект не найден."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=message)


class ValidationError(CRMError):
    def __init__(self, message: str = "Ошибка валидации."):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message)
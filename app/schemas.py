"""Pydantic-схемы для валидации входных/выходных данных API.

Все временные метки принимаются и отдаются в UTC (ISO 8601).
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator, field_serializer

UTC = ZoneInfo("UTC")


class ManagerCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Имя менеджера не может быть пустым.")
        return v.strip()


class ManagerResponse(ManagerCreate):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    @classmethod
    def _serialize_created_at(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return v.isoformat()


class CompanyCreate(BaseModel):
    name: str
    bin: str
    phone: str
    status: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Название организации не может быть пустым.")
        return v.strip()

    @field_validator("bin")
    @classmethod
    def _bin_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("БИН не может быть пустым.")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def _phone_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Телефон не может быть пустым.")
        return v.strip()

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"new", "in_progress", "meeting_set", "closed_won", "closed_lost", "archived"}
        if v not in allowed:
            raise ValueError(f"Статус должен быть одним из: {', '.join(sorted(allowed))}.")
        return v


class CompanyResponse(CompanyCreate):
    id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    @classmethod
    def _serialize_created_at(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return v.isoformat()


class CallCreate(BaseModel):
    company_id: int
    manager_id: int
    result: str
    meeting_id: Optional[int] = None
    note: Optional[str] = None

    @field_validator("result")
    @classmethod
    def _validate_result(cls, v: str) -> str:
        allowed = {"no_answer", "refused", "meeting_set"}
        if v not in allowed:
            raise ValueError(f"Результат звонка должен быть одним из: {', '.join(sorted(allowed))}.")
        return v


class CallResponse(BaseModel):
    id: int
    company_id: int
    manager_id: int
    result: str
    meeting_id: Optional[int]
    called_at: datetime
    note: Optional[str]

    model_config = {"from_attributes": True}

    @field_serializer("called_at")
    @classmethod
    def _serialize_called_at(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return v.isoformat()


class MeetingCreate(BaseModel):
    company_id: int
    manager_id: int
    scheduled_at: datetime  # UTC ISO 8601
    note: Optional[str] = None


class MeetingResponse(BaseModel):
    id: int
    company_id: int
    manager_id: int
    scheduled_at: datetime  # UTC ISO 8601
    duration_minutes: int
    status: str
    original_scheduled_at: Optional[datetime]
    created_at: datetime
    note: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_serializer("scheduled_at", "original_scheduled_at", "created_at")
    @classmethod
    def _serialize_dt(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return v.isoformat()


class MeetingUpdate(BaseModel):
    action: Optional[str] = None  # "reschedule" | "cancel"
    scheduled_at: Optional[datetime] = None  # нужно для reschedule
    note: Optional[str] = None

    @field_validator("action")
    @classmethod
    def _validate_action(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ("reschedule", "cancel"):
            raise ValueError("action должен быть 'reschedule' или 'cancel'.")
        return v

    @field_validator("scheduled_at")
    @classmethod
    def _require_time_for_reschedule(cls, v, info):
        if info.data.get("action") == "reschedule" and v is None:
            raise ValueError("Для переноса необходимо указать scheduled_at.")
        return v
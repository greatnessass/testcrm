"""HTTP-роутеры CRM API.

Все эндпоинты описаны здесь. Бизнес-логика delegated в app/services.py.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas, services

router = APIRouter()


# --- Организации ---

@router.post("/companies", response_model=schemas.CompanyResponse, status_code=201)
def create_company(data: schemas.CompanyCreate, db: Session = Depends(get_db)):
    return services.create_company(db, data)


@router.get("/companies")
def list_companies(
    status: Optional[str] = Query(None, description="Фильтр по статусу: new, in_progress, meeting_set, closed_won, closed_lost, archived"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    companies = services.get_companies(db, status=status, skip=skip, limit=limit)
    return {
        "items": [schemas.CompanyResponse.model_validate(c) for c in companies],
        "total": len(companies),
    }


# --- Менеджеры (вспомогательный, нужен для назначения встреч) ---

@router.post("/managers", response_model=schemas.ManagerResponse, status_code=201)
def create_manager(data: schemas.ManagerCreate, db: Session = Depends(get_db)):
    return services.create_manager(db, data)


# --- Звонки ---

@router.post("/calls", response_model=schemas.CallResponse, status_code=201)
def create_call(data: schemas.CallCreate, db: Session = Depends(get_db)):
    """Создаёт результат звонка.

    Требование №5: meeting_set без meeting_id — ошибка валидации.
    """
    return services.create_call(db, data)


# --- Встречи ---

@router.post("/meetings", response_model=schemas.MeetingResponse, status_code=201)
def create_meeting(data: schemas.MeetingCreate, db: Session = Depends(get_db)):
    return services.create_meeting(db, data)


@router.patch("/meetings/{meeting_id}", response_model=schemas.MeetingResponse)
def update_meeting(meeting_id: int, data: schemas.MeetingUpdate, db: Session = Depends(get_db)):
    return services.update_meeting(db, meeting_id, data)


@router.get("/managers/{manager_id}/schedule")
def get_schedule(
    manager_id: int,
    date: str = Query(..., description="Дата в формате YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    return services.get_manager_schedule(db, manager_id, date)

@router.get("/meetings/{meeting_id}/history")
def get_meeting_history(meeting_id: int, db: Session = Depends(get_db)):
    return services.get_meeting_history(db, meeting_id)
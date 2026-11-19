"""Бизнес-логика CRM.

Вся логика сосредоточена здесь. Роутеры только принимают запросы и возвращают ответы.
"""

from datetime import datetime, timedelta, time
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app import models
from app.exceptions import (
    MeetingConflictError,
    OutsideWorkingHoursError,
    NotFoundError,
    ValidationError,
)

# Часовой пояс Алматы: UTC+5, без перехода на летнее время.
ALMATY = ZoneInfo("Asia/Almaty")
UTC = ZoneInfo("UTC")

# Ровно 60 минут на встречу.
MEETING_DURATION = timedelta(minutes=60)

# Рабочие часы по Алматы: пн–пт, 09:00–18:00.
WORK_START_HOUR = 9
WORK_END_HOUR = 18


def _normalize_utc(dt: datetime) -> datetime:
    """Приводит datetime к naive UTC для хранения в БД.

    Если передана aware-дата с любым часовым поясом, конвертирует в UTC и убирает tzinfo.
    Если передана naive-дата, считает, что это уже UTC, и возвращает как есть.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _to_almaty(dt: datetime) -> datetime:
    """Переводит datetime (naive UTC или aware) в Asia/Almaty (aware)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ALMATY)


def _intervals_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Проверка пересечения двух интервалов [start, end).

    Интервалы полуоткрытые: [a_start, a_end) и [b_start, b_end).
    Пересечение есть, если a_start < b_end И b_start < a_end.
    Смежные слоты (например, 11:00–12:00 и 12:00–13:00) НЕ пересекаются,
    потому что 12:00 < 12:00 ложно. Это реализует требование «смежные слоты разрешены».
    """
    return a_start < b_end and b_start < a_end


def _check_working_hours(scheduled_at_utc: datetime):
    """Проверяет, что встреча целиком помещается в рабочий день.

    Рабочие дни: понедельник–пятница.
    Время: 09:00–18:00 по Asia/Almaty.
    Встреча длится 60 минут, поэтому начало должно быть >= 09:00,
    а окончание (начало + 60 мин) должно быть <= 18:00.
    """
    start_almaty = _to_almaty(scheduled_at_utc)
    end_almaty = start_almaty + MEETING_DURATION

    # weekday(): понедельник=0 … воскресенье=6. Выходные — 5 (суббота), 6 (воскресенье).
    if start_almaty.weekday() >= 5:
        raise OutsideWorkingHoursError(
            f"Встреча не может быть назначена на {start_almaty.strftime('%A')}. "
            f"Рабочие дни: понедельник–пятница."
        )

    # Начало не раньше 09:00.
    if start_almaty.hour < WORK_START_HOUR:
        raise OutsideWorkingHoursError(
            f"Встреча не может начинаться до {WORK_START_HOUR:02d}:00 по Алматы. "
            f"Запрошенное начало: {start_almaty.strftime('%H:%M')}."
        )

    # Окончание не позже 18:00.
    if end_almaty.hour > WORK_END_HOUR or (
        end_almaty.hour == WORK_END_HOUR and end_almaty.minute > 0
    ):
        raise OutsideWorkingHoursError(
            f"Встреча заканчивается в {end_almaty.strftime('%H:%M')} по Алматы, "
            f"что позже {WORK_END_HOUR:02d}:00. Встреча должна умещаться целиком в рабочий день."
        )

    # Начало не в 18:00 или позже (потому что тогда уложиться в 18:00 невозможно).
    if start_almaty.hour >= WORK_END_HOUR:
        raise OutsideWorkingHoursError(
            f"Встреча не может начинаться в {start_almaty.strftime('%H:%M')} или позже."
        )


def _check_manager_conflict(db: Session, manager_id: int, scheduled_at_utc: datetime,
                            exclude_meeting_id: Optional[int] = None):
    """Проверяет отсутствие пересекающихся встреч у менеджера.

    Учитываются только активные встречи (статус scheduled).
    exclude_meeting_id позволяет исключить саму встречу при переносе.
    """
    start = scheduled_at_utc
    end = scheduled_at_utc + MEETING_DURATION

    q = db.query(models.Meeting).filter(
        models.Meeting.manager_id == manager_id,
        models.Meeting.status == models.MeetingStatus.SCHEDULED.value,
    )
    if exclude_meeting_id is not None:
        q = q.filter(models.Meeting.id != exclude_meeting_id)

    for m in q.all():
        m_end = m.scheduled_at + MEETING_DURATION
        if _intervals_overlap(start, end, m.scheduled_at, m_end):
            m_almaty = _to_almaty(m.scheduled_at)
            m_end_almaty = m_almaty + MEETING_DURATION
            raise MeetingConflictError(
                f"У менеджера уже есть встреча {m.id} с "
                f"{m_almaty.strftime('%d.%m.%Y %H:%M')} по {m_end_almaty.strftime('%H:%M')} по Алматы. "
                f"Новая встреча пересекается."
            )


def _check_company_conflict(db: Session, company_id: int, scheduled_at_utc: datetime,
                            exclude_meeting_id: Optional[int] = None):
    """Проверяет, что у компании нет двух активных встреч одновременно.

    Даже с разными менеджерами у одной организации может быть только одна активная
    встреча в любой момент времени.
    """
    start = scheduled_at_utc
    end = scheduled_at_utc + MEETING_DURATION

    q = db.query(models.Meeting).filter(
        models.Meeting.company_id == company_id,
        models.Meeting.status == models.MeetingStatus.SCHEDULED.value,
    )
    if exclude_meeting_id is not None:
        q = q.filter(models.Meeting.id != exclude_meeting_id)

    for m in q.all():
        m_end = m.scheduled_at + MEETING_DURATION
        if _intervals_overlap(start, end, m.scheduled_at, m_end):
            raise MeetingConflictError(
                f"У компании уже есть активная встреча {m.id} в это время. "
                f"Две активные встречи на одну организацию одновременно запрещены."
            )


# ---------------------------------------------------------------------------
# CRUD-операции (бизнес-логика)
# ---------------------------------------------------------------------------

def create_manager(db: Session, data) -> models.Manager:
    manager = models.Manager(name=data.name, email=data.email, phone=data.phone)
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


def create_company(db: Session, data) -> models.Company:
    # Защита от дубликата БИНа: если такая организация уже существует — чистая ошибка, а не 500.
    existing = db.query(models.Company).filter(models.Company.bin == data.bin).first()
    if existing:
        raise ValidationError(f"Организация с БИН {data.bin} уже существует.")

    status = data.status or models.CompanyStatus.NEW.value
    company = models.Company(name=data.name, bin=data.bin, phone=data.phone, status=status)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def get_companies(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 100):
    q = db.query(models.Company)
    if status:
        q = q.filter(models.Company.status == status)
    return q.offset(skip).limit(limit).all()


def create_call(db: Session, data) -> models.Call:
    """Создаёт звонок.

    Требование №5: звонок с результатом meeting_set обязательно должен ссылаться
    на существующую встречу (meeting_id), иначе — ошибка валидации.
    """
    if data.result == models.CallResult.MEETING_SET.value:
        if data.meeting_id is None:
            raise ValidationError(
                "Звонок с результатом 'meeting_set' должен быть связан с встречей (укажите meeting_id)."
            )
        meeting = db.query(models.Meeting).filter(models.Meeting.id == data.meeting_id).first()
        if not meeting:
            raise ValidationError(f"Встреча {data.meeting_id} не найдена.")
        if meeting.status != models.MeetingStatus.SCHEDULED.value:
            raise ValidationError(
                f"Встреча {data.meeting_id} неактивна (статус '{meeting.status}')."
            )

    call = models.Call(
        company_id=data.company_id,
        manager_id=data.manager_id,
        result=data.result,
        meeting_id=data.meeting_id,
        note=data.note,
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


def create_meeting(db: Session, data) -> models.Meeting:
    """Создаёт встречу со всеми проверками бизнес-правил.

    Порядок проверок:
    1. Существуют ли менеджер и организация.
    2. Встреча попадает в рабочие часы (пн–пт, 09:00–18:00 Алматы, ровно 60 мин).
    3. Нет пересечения с другими встречами этого менеджера.
    4. Нет пересечения с другими активными встречами этой организации.
    """
    manager = db.query(models.Manager).filter(models.Manager.id == data.manager_id).first()
    if not manager:
        raise NotFoundError(f"Менеджер {data.manager_id} не найден.")

    company = db.query(models.Company).filter(models.Company.id == data.company_id).first()
    if not company:
        raise NotFoundError(f"Организация {data.company_id} не найдена.")

    scheduled_at = _normalize_utc(data.scheduled_at)

    # Проверка рабочих часов.
    _check_working_hours(scheduled_at)

    # Проверка пересечений.
    _check_manager_conflict(db, data.manager_id, scheduled_at)
    _check_company_conflict(db, data.company_id, scheduled_at)

    meeting = models.Meeting(
        company_id=data.company_id,
        manager_id=data.manager_id,
        scheduled_at=scheduled_at,
        duration_minutes=60,
        status=models.MeetingStatus.SCHEDULED.value,
        original_scheduled_at=scheduled_at,
    )
    db.add(meeting)
    db.flush()

    # История: встреча создана.
    db.add(models.MeetingHistory(
        meeting_id=meeting.id,
        action="created",
        new_scheduled_at=scheduled_at,
        note=data.note,
    ))

    db.commit()
    db.refresh(meeting)
    return meeting


def update_meeting(db: Session, meeting_id: int, data) -> models.Meeting:
    """Переносит или отменяет встречу, сохраняя историю изменений.

    При переносе (reschedule) выполняются те же проверки, что при создании:
    рабочие часы + отсутствие пересечений (сам встречу исключаем).
    """
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise NotFoundError(f"Встреча {meeting_id} не найдена.")

    action = (data.action or "").lower()

    if action == "cancel":
        meeting.status = models.MeetingStatus.CANCELLED.value
        db.add(models.MeetingHistory(
            meeting_id=meeting.id,
            action="cancelled",
            previous_scheduled_at=meeting.scheduled_at,
            note=data.note,
        ))
        db.commit()
        db.refresh(meeting)
        return meeting

    if action == "reschedule":
        if data.scheduled_at is None:
            raise ValidationError("Для переноса необходимо указать scheduled_at.")

        new_time = _normalize_utc(data.scheduled_at)

        _check_working_hours(new_time)
        _check_manager_conflict(db, meeting.manager_id, new_time, exclude_meeting_id=meeting.id)
        _check_company_conflict(db, meeting.company_id, new_time, exclude_meeting_id=meeting.id)

        old_time = meeting.scheduled_at
        meeting.scheduled_at = new_time
        # original_scheduled_at сохраняет первое время создания встречи.
        if meeting.original_scheduled_at is None:
            meeting.original_scheduled_at = old_time

        db.add(models.MeetingHistory(
            meeting_id=meeting.id,
            action="rescheduled",
            previous_scheduled_at=old_time,
            new_scheduled_at=new_time,
            note=data.note,
        ))

        db.commit()
        db.refresh(meeting)
        return meeting

    raise ValidationError("action должен быть 'reschedule' или 'cancel'.")


def get_manager_schedule(db: Session, manager_id: int, date_str: str) -> dict:
    """Возвращает расписание менеджера на указанный день (YYYY-MM-DD).

    Встречи ищутся в интервале соответствующего календарного дня по Алматы.
    """
    manager = db.query(models.Manager).filter(models.Manager.id == manager_id).first()
    if not manager:
        raise NotFoundError(f"Менеджер {manager_id} не найден.")

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Параметр date должен быть в формате YYYY-MM-DD.")

    # Границы суток в Алматы, приведённые к UTC для запроса к БД.
    day_start_almaty = datetime.combine(target_date, time.min, tzinfo=ALMATY)
    day_end_almaty = day_start_almaty + timedelta(days=1)
    day_start_utc = day_start_almaty.astimezone(UTC).replace(tzinfo=None)
    day_end_utc = day_end_almaty.astimezone(UTC).replace(tzinfo=None)

    meetings = db.query(models.Meeting).filter(
        models.Meeting.manager_id == manager_id,
        models.Meeting.scheduled_at >= day_start_utc,
        models.Meeting.scheduled_at < day_end_utc,
        models.Meeting.status == models.MeetingStatus.SCHEDULED.value,
    ).order_by(models.Meeting.scheduled_at).all()

    return {
        "manager_id": manager_id,
        "date": date_str,
        "meetings": [
            {
                "id": m.id,
                "company_id": m.company_id,
                "scheduled_at": m.scheduled_at.isoformat() + "Z",
                "scheduled_at_almaty": _to_almaty(m.scheduled_at).isoformat(),
                "status": m.status,
            }
            for m in meetings
        ],
    }
    
def get_meeting_history(db: Session, meeting_id: int):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise NotFoundError(f"Встреча {meeting_id} не найдена.")
    return [
        {"action": h.action, "changed_at": h.changed_at, "previous": h.previous_scheduled_at, "new": h.new_scheduled_at}
        for h in meeting.history
    ]
    
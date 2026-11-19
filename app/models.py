"""SQLAlchemy-модели данных.

Описывают таблицы базы данных: менеджеры, организации, звонки, встречи и история изменений встреч.
Все временные метки хранятся в UTC (в БД записываются naive UTC datetime).
"""

import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CompanyStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    MEETING_SET = "meeting_set"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    ARCHIVED = "archived"


class CallResult(str, enum.Enum):
    NO_ANSWER = "no_answer"
    REFUSED = "refused"
    MEETING_SET = "meeting_set"


class MeetingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Manager(Base):
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    calls = relationship("Call", back_populates="manager")
    meetings = relationship("Meeting", back_populates="manager")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    bin = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    status = Column(String, default=CompanyStatus.NEW.value)
    created_at = Column(DateTime, default=func.now())

    calls = relationship("Call", back_populates="company")
    meetings = relationship("Meeting", back_populates="company")


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey("managers.id"), nullable=False, index=True)
    result = Column(String, nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    called_at = Column(DateTime, default=func.now())
    note = Column(String, nullable=True)

    company = relationship("Company", back_populates="calls")
    manager = relationship("Manager", back_populates="calls")
    meeting = relationship("Meeting", back_populates="calls")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey("managers.id"), nullable=False, index=True)
    scheduled_at = Column(DateTime, nullable=False, index=True)  # UTC
    duration_minutes = Column(Integer, default=60)
    status = Column(String, default=MeetingStatus.SCHEDULED.value)
    original_scheduled_at = Column(DateTime, nullable=True)  # UTC — первое запланированное время
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="meetings")
    manager = relationship("Manager", back_populates="meetings")
    calls = relationship("Call", back_populates="meeting")
    history = relationship("MeetingHistory", back_populates="meeting", order_by="MeetingHistory.changed_at")


class MeetingHistory(Base):
    __tablename__ = "meeting_history"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    action = Column(String, nullable=False)  # created | rescheduled | cancelled
    previous_scheduled_at = Column(DateTime, nullable=True)  # UTC
    new_scheduled_at = Column(DateTime, nullable=True)  # UTC
    changed_at = Column(DateTime, default=func.now())
    note = Column(String, nullable=True)

    meeting = relationship("Meeting", back_populates="history")
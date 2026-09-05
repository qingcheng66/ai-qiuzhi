from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 10 阶段求职状态机
STAGES = [
    "投递",
    "测评",
    "笔试",
    "简历评估",
    "一面",
    "二面",
    "三面",
    "HR面",
    "Offer评估",
    "Offer",
]
STAGE_KEYS = [
    "applied",
    "assessment",
    "written_test",
    "resume_review",
    "interview_1",
    "interview_2",
    "interview_3",
    "hr_interview",
    "offer_eval",
    "offer",
]
MAX_STAGE = len(STAGES) - 1


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    website: Mapped[str] = mapped_column(String(500), default="")
    industry: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="companies")  # noqa: F821
    positions: Mapped[list["Position"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    jd_raw: Mapped[str] = mapped_column(Text, default="")
    jd_structured: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="positions")  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(
        ForeignKey("positions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    current_stage: Mapped[int] = mapped_column(Integer, default=0)
    stages: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    applied_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    position: Mapped["Position"] = relationship(back_populates="applications")  # noqa: F821
    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    resume_versions: Mapped[list["ResumeVersion"]] = relationship(  # noqa: F821
        back_populates="application", cascade="all, delete-orphan"
    )


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    stage_index: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(100), default="")
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interviewers: Mapped[list[Any]] = mapped_column(JSON, default=list)
    result: Mapped[str] = mapped_column(String(50), default="")  # pass/fail/pending
    feedback: Mapped[str] = mapped_column(Text, default="")

    application: Mapped["Application"] = relationship(back_populates="interviews")  # noqa: F821
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
    name: str
    website: str = ""
    industry: str = ""


class CompanyCreate(BaseModel):
    name: str
    website: str = ""
    industry: str = ""
    user_id: int | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    industry: str | None = None


class PositionBase(BaseModel):
    company_id: int
    title: str
    jd_raw: str = ""
    jd_structured: dict[str, Any] = {}


class PositionCreate(PositionBase):
    user_id: int | None = None


class PositionOut(PositionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    website: str = ""
    industry: str = ""
    created_at: datetime


class ApplicationBase(BaseModel):
    position_id: int
    current_stage: int = 0
    notes: str = ""
    applied_date: datetime | None = None


class ApplicationCreate(ApplicationBase):
    user_id: int | None = None


class StageAdvance(BaseModel):
    target: int | None = None


class InterviewBase(BaseModel):
    application_id: int
    stage_index: int
    type: str = ""
    date: datetime
    interviewers: list[str] = []
    result: str = ""
    feedback: str = ""


class InterviewCreate(InterviewBase):
    pass


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    stage_index: int
    type: str
    date: datetime
    interviewers: list[Any]
    result: str
    feedback: str


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position_id: int
    current_stage: int
    stages: dict[str, Any]
    notes: str
    applied_date: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationOut):
    position: PositionOut | None = None
    company: CompanyOut | None = None
    interviews: list[InterviewOut] = []
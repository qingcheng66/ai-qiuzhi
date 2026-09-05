from typing import Any

from pydantic import BaseModel, Field


class ResumeGenerateRequest(BaseModel):
    """简历生成请求"""
    jd: str
    job_title: str = ""
    company: str = ""
    user_id: int | None = None


class ResumeUpdate(BaseModel):
    title: str | None = None
    content: dict[str, Any] | None = None
    template_id: int | None = None
    position_id: int | None = None


class ExportRequest(BaseModel):
    format: str = Field(pattern="^(html|pdf|docx)$")
    template_id: int | None = None


class CreateDraftRequest(BaseModel):
    template_id: int | None = None
    title: str = "新建简历"
    initial_content: dict[str, Any] | None = None


class AiGenerateRequest(BaseModel):
    jd: str


class SectionUpdateRequest(BaseModel):
    content: Any


class SectionRegenerateRequest(BaseModel):
    jd: str
    jd_structured: dict[str, Any] | None = None
    matches: list[dict] | None = None
    used_source: str | None = None


class LinkPositionRequest(BaseModel):
    position_id: int


class FinalizeRequest(BaseModel):
    change_log: str = "定稿"


class ResumeDataOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    position_id: int | None
    title: str
    content: dict[str, Any]
    template_id: int | None
    source: str
    status: str
    created_at: Any
    updated_at: Any


class ResumeSectionOut(BaseModel):
    section: str
    content: Any
    section_names: list[str] = Field(default=[
        "basics", "education", "skills", "projects", "experience", "highlights"
    ])


class ResumeVersionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    application_id: int
    resume_data_id: int | None
    version: int
    change_log: str
    content: dict[str, Any]
    created_at: Any
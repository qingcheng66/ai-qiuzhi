from typing import Any

from pydantic import BaseModel


class StructurizeRequest(BaseModel):
    text: str
    user_id: int | None = None


class WikiMatchRequest(BaseModel):
    skills: list[str]
    job_title: str = ""
    limit: int = 5
    user_id: int | None = None


class WikiMatchItem(BaseModel):
    source: str  # kb | wiki
    type: str  # project | skill | highlight | experience
    name: str
    content: str
    score: float = 0
    meta: dict[str, Any] = {}


class WikiMatchResponse(BaseModel):
    matches: list[WikiMatchItem]
    used_source: str  # 主要数据源说明


class JDStructured(BaseModel):
    company: str = ""
    title: str = ""
    skills_required: list[str] = []
    responsibilities: list[str] = []
    description_summary: str = ""


class ResumeContent(BaseModel):
    """AI 生成的结构化简历内容"""

    basics: dict[str, Any] = {}
    education: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    experience: list[dict[str, Any]] = []
    highlights: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}
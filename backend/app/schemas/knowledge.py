from typing import Any

from pydantic import BaseModel


class KbProfileIn(BaseModel):
    name: str = ""
    label: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    birth: str = ""
    github: str = ""
    blog: str = ""
    summary: str = ""
    education: list[dict[str, Any]] = []


class KbProfileOut(KbProfileIn):
    id: int
    user_id: int


class KbProjectIn(BaseModel):
    name: str
    description: str = ""
    highlights: list[str] = []
    role: str = ""
    url: str = ""
    start_date: str = ""
    end_date: str = ""
    keywords: list[str] = []
    enabled: bool = True
    sort_order: int = 0


class KbProjectOut(KbProjectIn):
    id: int
    user_id: int


class KbSkillIn(BaseModel):
    name: str
    keywords: list[str] = []
    level: str = ""
    enabled: bool = True
    sort_order: int = 0


class KbSkillOut(KbSkillIn):
    id: int
    user_id: int


class KbHighlightIn(BaseModel):
    title: str
    category: str = ""
    content: str = ""
    metrics: dict[str, Any] = {}
    enabled: bool = True
    sort_order: int = 0


class KbHighlightOut(KbHighlightIn):
    id: int
    user_id: int


class KbExperienceIn(BaseModel):
    company: str
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    highlights: list[str] = []
    enabled: bool = True
    sort_order: int = 0


class KbExperienceOut(KbExperienceIn):
    id: int
    user_id: int


class KbSortUpdate(BaseModel):
    id: int
    sort_order: int


class KbToggleUpdate(BaseModel):
    enabled: bool


class KbChunkIn(BaseModel):
    title: str
    content: str = ""
    tags: list[str] = []
    enabled: bool = True
    sort_order: int = 0


class KbChunkOut(KbChunkIn):
    id: int
    user_id: int
    category_id: int
    created_at: str | None = None
    updated_at: str | None = None


class KbCategoryIn(BaseModel):
    name: str
    icon: str = "folder"
    color: str = "blue"
    sort_order: int = 0


class KbCategoryOut(KbCategoryIn):
    id: int
    user_id: int
    chunks: list[KbChunkOut] = []


class KbBundle(BaseModel):
    """一次拉取全部知识库数据"""

    profile: KbProfileOut | None = None
    projects: list[KbProjectOut] = []
    skills: list[KbSkillOut] = []
    highlights: list[KbHighlightOut] = []
    experiences: list[KbExperienceOut] = []
    categories: list[KbCategoryOut] = []
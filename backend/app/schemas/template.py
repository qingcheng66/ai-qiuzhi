from typing import Any

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    content: str = ""
    variables: list[str] = []
    type: str = "custom"
    is_builtin: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None
    variables: list[str] | None = None


class TemplateRenderRequest(BaseModel):
    content: dict[str, Any]


class TemplateOut(BaseModel):
    id: int
    name: str
    description: str
    type: str
    source: str
    content: str
    variables: list[Any]
    is_builtin: bool
    created_at: Any
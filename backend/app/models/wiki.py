from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WikiCache(Base):
    """只读导入的 wiki 缓存（按分类一条记录）"""

    __tablename__ = "wiki_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parsed_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_path: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WikiProject(Base):
    __tablename__ = "wiki_projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wiki_cache_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    highlights: Mapped[list[Any]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[Any]] = mapped_column(JSON, default=list)
    url: Mapped[str] = mapped_column(String(500), default="")
    date_range: Mapped[str] = mapped_column(String(100), default="")


class WikiSkill(Base):
    __tablename__ = "wiki_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wiki_cache_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255))
    keywords: Mapped[list[Any]] = mapped_column(JSON, default=list)


class WikiHighlight(Base):
    __tablename__ = "wiki_highlights"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wiki_cache_id: Mapped[int] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
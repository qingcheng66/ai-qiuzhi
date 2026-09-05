"""知识库服务：应用内可编辑数据(profile/projects/skills/highlights/experiences)"""
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import (
    KbExperience,
    KbHighlight,
    KbProfile,
    KbProject,
    KbSkill,
)


def get_profile(session: Session, user_id: int) -> dict[str, Any]:
    prof = session.scalars(
        select(KbProfile).where(KbProfile.user_id == user_id)
    ).first()
    if not prof:
        return {
            "name": "",
            "label": "",
            "email": "",
            "phone": "",
            "location": "",
            "birth": "",
            "github": "",
            "blog": "",
            "summary": "",
            "education": [],
        }
    return {
        "name": prof.name,
        "label": prof.label,
        "email": prof.email,
        "phone": prof.phone,
        "location": prof.location,
        "birth": prof.birth,
        "github": prof.github,
        "blog": prof.blog,
        "summary": prof.summary,
        "education": prof.education or [],
    }


def get_bundle(session: Session, user_id: int) -> dict[str, Any]:
    """一次拉取全部分类数据，供前端知识库页面"""
    def _rows(model):
        return session.scalars(
            select(model)
            .where(model.user_id == user_id)
            .order_by(model.sort_order, model.id)
        ).all()

    prof = session.scalars(
        select(KbProfile).where(KbProfile.user_id == user_id)
    ).first()

    # 查 v2 栏目和卡片；如果为空则初始化预设栏目
    from app.models.knowledge import KbCategory, KbChunk
    categories = session.scalars(
        select(KbCategory)
        .where(KbCategory.user_id == user_id)
        .order_by(KbCategory.sort_order, KbCategory.id)
    ).all()

    if not categories:
        defaults = [
            ("个人核心定位与亮点", "sparkles", "blue"),
            ("项目深挖与技术难点", "code-bracket", "indigo"),
            ("架构与高并发实践", "server-stack", "emerald"),
            ("开源与个人影响力", "globe-alt", "amber"),
        ]
        for idx, (cname, icon, color) in enumerate(defaults):
            cat = KbCategory(user_id=user_id, name=cname, icon=icon, color=color, sort_order=idx)
            session.add(cat)
        session.commit()
        categories = session.scalars(
            select(KbCategory)
            .where(KbCategory.user_id == user_id)
            .order_by(KbCategory.sort_order, KbCategory.id)
        ).all()

    # 组装 categories 及其 chunks
    cat_list = []
    for cat in categories:
        chunks = session.scalars(
            select(KbChunk)
            .where(KbChunk.category_id == cat.id)
            .order_by(KbChunk.sort_order, KbChunk.id)
        ).all()
        cat_list.append({
            "id": cat.id,
            "user_id": cat.user_id,
            "name": cat.name,
            "icon": cat.icon,
            "color": cat.color,
            "sort_order": cat.sort_order,
            "chunks": [
                {
                    "id": ch.id,
                    "user_id": ch.user_id,
                    "category_id": ch.category_id,
                    "title": ch.title,
                    "content": ch.content,
                    "tags": ch.tags or [],
                    "enabled": ch.enabled,
                    "sort_order": ch.sort_order,
                    "created_at": ch.created_at.isoformat() if ch.created_at else None,
                    "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
                }
                for ch in chunks
            ],
        })

    return {
        "profile": {
            "id": prof.id,
            "user_id": user_id,
            **get_profile(session, user_id),
        }
        if prof
        else None,
        "projects": _rows(KbProject),
        "skills": _rows(KbSkill),
        "highlights": _rows(KbHighlight),
        "experiences": _rows(KbExperience),
        "categories": cat_list,
    }



def upsert_profile(session: Session, user_id: int, data: dict[str, Any]) -> KbProfile:
    prof = session.scalars(
        select(KbProfile).where(KbProfile.user_id == user_id)
    ).first()
    if not prof:
        prof = KbProfile(user_id=user_id)
        session.add(prof)
    for k, v in data.items():
        setattr(prof, k, v)
    session.commit()
    session.refresh(prof)
    return prof


def import_kb_from_json(session: Session, user_id: int, data: dict[str, Any]) -> dict[str, int]:
    """从标准简历 JSON（JSON Resume 兼容或本应用结构）导入知识库。

    幂等：先清空该用户已有的 projects/skills/experiences（保留 profile 合并）。
    """
    counts = {"profile": 0, "projects": 0, "skills": 0, "experiences": 0, "highlights": 0}

    # 清空已有列表类数据，避免重复导入
    for model in (KbProject, KbSkill, KbExperience):
        for obj in session.scalars(select(model).where(model.user_id == user_id)):
            session.delete(obj)
    session.flush()

    basics = data.get("basics") or {}
    if basics:
        upsert_profile(
            session,
            user_id,
            {
                "name": basics.get("name", ""),
                "label": basics.get("label", ""),
                "email": basics.get("email", ""),
                "phone": basics.get("phone", ""),
                "location": (basics.get("location") or {}).get("city", "") if isinstance(basics.get("location"), dict) else basics.get("location", ""),
                "github": next((p.get("url", "") for p in basics.get("profiles", []) if "github" in (p.get("network") or "").lower()), ""),
                "blog": next((p.get("url", "") for p in basics.get("profiles", []) if "blog" in (p.get("network") or "").lower()), ""),
                "summary": basics.get("summary", ""),
                "education": data.get("education", []) or [],
            },
        )
        counts["profile"] = 1

    for p in data.get("projects", []) or []:
        session.add(
            KbProject(
                user_id=user_id,
                name=p.get("name", "未命名项目"),
                description=p.get("description", ""),
                highlights=p.get("highlights", []) or [],
                keywords=p.get("keywords", []) or [],
                role=p.get("role", ""),
                url=p.get("url", ""),
                start_date=p.get("startDate", ""),
                end_date=p.get("endDate", ""),
            )
        )
        counts["projects"] += 1

    for i, s in enumerate(data.get("skills", []) or []):
        session.add(
            KbSkill(
                user_id=user_id,
                name=s.get("name", f"技能{i+1}"),
                keywords=s.get("keywords", []) or [],
                level=s.get("level", ""),
                sort_order=i,
            )
        )
        counts["skills"] += 1

    for i, w in enumerate(data.get("work", []) or []):
        session.add(
            KbExperience(
                user_id=user_id,
                company=w.get("company", ""),
                role=w.get("position", ""),
                start_date=w.get("startDate", ""),
                end_date=w.get("endDate", ""),
                highlights=w.get("highlights", []) or [],
                sort_order=i,
            )
        )
        counts["experiences"] += 1

    session.commit()
    return counts


def parse_import_text(text: str) -> dict[str, Any] | None:
    """尝试解析导入文本为 JSON"""
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
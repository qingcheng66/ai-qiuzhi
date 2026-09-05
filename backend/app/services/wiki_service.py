"""双源匹配：应用内可编辑知识库(kb_*) + 只读导入 wiki 缓存('wiki_cache')

对每个 JD 技能关键词计算命中分数，返回带来源标注(top)的匹配项。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KbExperience, KbHighlight, KbProject, KbSkill
from app.models.wiki import WikiCache, WikiHighlight, WikiProject, WikiSkill


def _hit_score(text: str, keywords: list[str], job_title: str = "") -> tuple[int, set[str]]:
    """返回(匹配关键词数, 命中的关键词集合)"""
    text_l = (text or "").lower()
    hit = set()
    for kw in keywords:
        kw_l = (kw or "").strip().lower()
        if kw_l and kw_l in text_l:
            hit.add(kw)
    if job_title:
        jt = job_title.lower()
        if jt and jt in text_l:
            hit.add(jt)
    return len(hit), hit


def collect_skill_keywords(session: Session, user_id: int) -> list[str]:
    """从 kb_skills + wiki 技能聚合所有关键词，供 JD 匹配"""
    kws: set[str] = set()
    for sk in session.scalars(
        select(KbSkill).where(KbSkill.user_id == user_id, KbSkill.enabled.is_(True))
    ):
        kws.add(sk.name)
        if sk.keywords:
            kws.update(sk.keywords)
    for ws in session.scalars(select(WikiSkill)):
        kws.add(ws.name)
        if ws.keywords:
            kws.update(ws.keywords)
    return [k for k in kws if k]


def match_kb(session: Session, user_id: int, skills: list[str], job_title: str = "", limit: int = 5) -> list[dict]:
    """从应用内知识库匹配"""
    items: list[dict] = []

    projects = session.scalars(
        select(KbProject)
        .where(KbProject.user_id == user_id, KbProject.enabled.is_(True))
        .order_by(KbProject.sort_order)
    ).all()
    for p in projects:
        hay = "\n".join(
            [p.name, p.description, " ".join(p.highlights or []), " ".join(p.keywords or [])]
        )
        score, hit = _hit_score(hay, skills, job_title)
        if score > 0:
            items.append(
                {
                    "source": "kb",
                    "type": "project",
                    "name": p.name,
                    "content": "\n".join(p.highlights or []) or p.description,
                    "score": score / max(len(skills), 1),
                    "meta": {"hit": list(hit), "id": p.id, "role": p.role, "date": f"{p.start_date}~{p.end_date}", "url": p.url},
                }
            )

    skills_kb = session.scalars(
        select(KbSkill).where(KbSkill.user_id == user_id, KbSkill.enabled.is_(True))
    ).all()
    for s in skills_kb:
        hay = " ".join([s.name, " ".join(s.keywords or [])])
        score, hit = _hit_score(hay, skills, job_title)
        if score > 0:
            items.append(
                {
                    "source": "kb",
                    "type": "skill",
                    "name": s.name,
                    "content": " / ".join(s.keywords or []) or s.name,
                    "score": score / max(len(skills), 1),
                    "meta": {"hit": list(hit), "id": s.id, "level": s.level},
                }
            )

    highlights = session.scalars(
        select(KbHighlight)
        .where(KbHighlight.user_id == user_id, KbHighlight.enabled.is_(True))
        .order_by(KbHighlight.sort_order)
    ).all()
    for h in highlights:
        hay = " ".join([h.title, h.content, h.category])
        score, hit = _hit_score(hay, skills, job_title)
        if score > 0:
            items.append(
                {
                    "source": "kb",
                    "type": "highlight",
                    "name": h.title,
                    "content": h.content,
                    "score": score / max(len(skills), 1) + 0.1,
                    "meta": {"hit": list(hit), "id": h.id, "category": h.category, "metrics": h.metrics},
                }
            )

    exps = session.scalars(
        select(KbExperience).where(KbExperience.user_id == user_id, KbExperience.enabled.is_(True))
    )
    for e in exps:
        hay = "\n".join([e.company, e.role, " ".join(e.highlights or [])])
        score, hit = _hit_score(hay, skills, job_title)
        if score > 0:
            items.append(
                {
                    "source": "kb",
                    "type": "experience",
                    "name": e.company,
                    "content": "\n".join(e.highlights or []),
                    "score": score / max(len(skills), 1),
                    "meta": {"hit": list(hit), "id": e.id, "role": e.role, "date": f"{e.start_date}~{e.end_date}"},
                }
            )

    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:limit]


def match_wiki(session: Session, skills: list[str], job_title: str = "", limit: int = 5) -> list[dict]:
    """从只读 wiki 缓存匹配"""
    items: list[dict] = []

    for p in session.scalars(select(WikiProject)):
        hay = "\n".join([p.name, p.description, " ".join(p.highlights or []), " ".join(p.keywords or [])])
        score, hit = _hit_score(hay, skills, job_title)
        if score > 0:
            items.append(
                {
                    "source": "wiki",
                    "type": "project",
                    "name": p.name,
                    "content": "\n".join(p.highlights or []) or p.description,
                    "score": score / max(len(skills), 1),
                    "meta": {"hit": list(hit), "id": p.id, "date": p.date_range, "url": p.url},
                }
            )

    for h in session.scalars(select(WikiHighlight)):
        hay = " ".join([h.title, h.content, h.category])
        score, hit = _hit_score(hay, skills, job_title)
        if score > 0:
            items.append(
                {
                    "source": "wiki",
                    "type": "highlight",
                    "name": h.title,
                    "content": h.content,
                    "score": score / max(len(skills), 1) + 0.1,
                    "meta": {"hit": list(hit), "id": h.id, "category": h.category, "metrics": h.metrics},
                }
            )

    for w in session.scalars(select(WikiSkill)):
        hay = " ".join([w.name, " ".join(w.keywords or [])])
        score, hit = _hit_score(hay, skills, job_title)
        if score > 0:
            items.append(
                {
                    "source": "wiki",
                    "type": "skill",
                    "name": w.name,
                    "content": " / ".join(w.keywords or []) or w.name,
                    "score": score / max(len(skills), 1),
                    "meta": {"hit": list(hit), "id": w.id},
                }
            )

    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:limit]


def dual_match(session: Session, user_id: int, skills: list[str], job_title: str = "", limit: int = 5) -> dict:
    """合并双源，kb 结果优先展示与打分加权"""
    kb_items = match_kb(session, user_id, skills, job_title, limit=limit)
    wiki_items = match_wiki(session, skills, job_title, limit=limit)
    merged = kb_items + wiki_items
    # kb 优先（同分排前）
    for it in kb_items:
        it["score"] = it["score"] * 1.2
    merged.sort(key=lambda x: (x["source"] != "kb", -x["score"]))
    merged = merged[:limit]
    used_source = "kb+wiki" if kb_items and wiki_items else ("kb" if kb_items else ("wiki" if wiki_items else "none"))
    return {"matches": merged, "used_source": used_source}
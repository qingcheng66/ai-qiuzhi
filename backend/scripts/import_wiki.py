"""一次性的知识库双写导入脚本

数据源：
  1. /Users/apple/resume/resume.json               → kb 表 + wiki_cache(profile)
  2. /Users/apple/knowledge/career/resume-highlights.md → wiki_cache(highlights) + wiki_highlights
  3. /Users/apple/knowledge/career/resume-h3c-java.md   → wiki_cache(resume-h3c)
  4. /Users/apple/knowledge/career/resume-qunar-ai-fullstack.md → wiki_cache(resume-qunar)

同时：
  - 创建/复用默认用户（刘仁晓君）
  - 创建 3 套内置模板（minimal / twocolumn / tech）

用法：
  .venv/bin/python -m scripts.import_wiki
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import stages  # noqa: F401  (仅确保核心导入)
from app.database import SessionLocal, create_all
from app.models.knowledge import (
    KbExperience,
    KbHighlight,
    KbProfile,
    KbProject,
    KbSkill,
)
from app.models.template import Template
from app.models.user import User
from app.models.wiki import WikiCache, WikiHighlight, WikiProject, WikiSkill
from app.services import knowledge_service

RESUME_JSON = Path("/Users/apple/resume/resume.json")
CAREER_DIR = Path("/Users/apple/knowledge/career")

# 内置模板：从 template_static/*.j2 读取，作为 builtin 模板入库
TEMPLATE_STATIC = Path(__file__).resolve().parent.parent / "app" / "template_static"


def ensure_default_user(session) -> User:
    user = session.query(User).filter(User.is_default.is_(True)).first()
    if not user:
        user = User(
            email="1120835055@qq.com",
            name="刘仁晓君",
            is_default=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"[user] 创建默认用户: id={user.id} {user.name}")
    else:
        print(f"[user] 复用默认用户: id={user.id} {user.name}")
    return user


def import_resume_json(session, user: User) -> None:
    """从 resume.json 双写：kb 表（可编辑）+ wiki_cache(profile/projects/skills)"""
    if not RESUME_JSON.exists():
        print(f"[skip] 未找到 {RESUME_JSON}")
        return

    data = json.loads(RESUME_JSON.read_text(encoding="utf-8"))

    # 1) 写 kb 表（应用内可编辑主数据）
    counts = knowledge_service.import_kb_from_json(session, user.id, data)
    print(f"[kb] 导入应用内知识库: {counts}")

    # 2) 写 wiki_cache（只读快照，供「来源=wiki」展示）
    cache = WikiCache(
        category="profile",
        raw_text=RESUME_JSON.read_text(encoding="utf-8"),
        parsed_json=data,
        source_path=str(RESUME_JSON),
    )
    session.add(cache)
    session.flush()

    # profile 单条
    basics = data.get("basics", {})
    session.add(
        WikiProject(
            wiki_cache_id=cache.id,
            name="个人信息",
            description=basics.get("label", ""),
            highlights=[],
            keywords=[],
            url="",
            date_range="",
        )
    )
    # projects
    for p in data.get("projects", []):
        session.add(
            WikiProject(
                wiki_cache_id=cache.id,
                name=p.get("name", ""),
                description=p.get("description", ""),
                highlights=p.get("highlights", []),
                keywords=p.get("keywords", []),
                url=p.get("url", ""),
                date_range=f"{p.get('startDate', '')}~{p.get('endDate', '')}",
            )
        )
    # skills
    for s in data.get("skills", []):
        session.add(
            WikiSkill(
                wiki_cache_id=cache.id,
                name=s.get("name", ""),
                keywords=s.get("keywords", []),
            )
        )
    session.commit()
    print("[wiki] 导入 resume.json → wiki_cache #%d" % cache.id)


def import_highlights_md(session, user: User) -> None:
    """解析 resume-highlights.md → wiki_highlights 条目"""
    fp = CAREER_DIR / "resume-highlights.md"
    if not fp.exists():
        print(f"[skip] 未找到 {fp}")
        return

    text = fp.read_text(encoding="utf-8")
    cache = WikiCache(
        category="highlights",
        raw_text=text,
        parsed_json={},
        source_path=str(fp),
    )
    session.add(cache)
    session.flush()

    # 简单解析：按数字列表拆条
    # 匹配 "N. **标题**：内容" 模式
    pattern = re.compile(r"^\s*(\d+)\.\s+\*\*(.+?)\*\*(?:[:：]\s*(.*))?$", re.M)
    items = []
    for m in pattern.finditer(text):
        title = m.group(2).strip()
        content = (m.group(3) or "").strip()
        # 归属分类：用前面最近的 "## " 标题
        before = text[: m.start()]
        cats = re.findall(r"^##\s+(.+)$", before, re.M)
        category = cats[-1].strip() if cats else ""
        items.append((category, title, content))

    for category, title, content in items:
        session.add(
            WikiHighlight(
                wiki_cache_id=cache.id,
                title=title,
                category=category,
                content=content,
                metrics={},
            )
        )

    # 同步一条到 kb_highlights（应用内可编辑，便于用户直接改亮点）
    for i, (category, title, content) in enumerate(items[:24]):
        session.add(
            KbHighlight(
                user_id=user.id,
                title=title,
                category=category,
                content=content,
                sort_order=i,
            )
        )

    session.commit()
    print(f"[wiki] 导入 highlights: {len(items)} 条 → wiki_highlights + kb_highlights")


def import_resume_docs(session, user: User) -> None:
    """把针对性简历 md 文档也导入 wiki_cache（作为参考上下文）"""
    for fn in ("resume-h3c-java.md", "resume-qunar-ai-fullstack.md"):
        fp = CAREER_DIR / fn
        if not fp.exists():
            continue
        session.add(
            WikiCache(
                category=f"resume-{fn.removeprefix('resume-').removesuffix('.md')}",
                raw_text=fp.read_text(encoding="utf-8"),
                parsed_json={},
                source_path=str(fp),
            )
        )
    session.commit()
    print("[wiki] 导入 2 份针对性简历文档")


def seed_builtin_templates(session, user: User) -> None:
    names = ["minimal", "twocolumn", "tech"]
    for name in names:
        fp = TEMPLATE_STATIC / f"{name}.j2"
        if not fp.exists():
            print(f"[warn] 模板文件缺失: {fp}")
            continue
        existing = session.query(Template).filter(Template.name == name).first()
        if existing:
            print(f"[tpl] 已存在: {name}")
            continue
        session.add(
            Template(
                user_id=user.id,
                name=name,
                description={"minimal": "简约单栏（通用）", "twocolumn": "双栏（技能+教育在左）", "tech": "技术风（等宽字体）"}[name],
                type="builtin",
                source="html",
                content=fp.read_text(encoding="utf-8"),
                variables=[],
                is_builtin=True,
            )
        )
    session.commit()
    print("[tpl] 内置模板入库完成")


def main():
    create_all()
    session = SessionLocal()
    try:
        user = ensure_default_user(session)
        import_resume_json(session, user)
        import_highlights_md(session, user)
        import_resume_docs(session, user)
        seed_builtin_templates(session, user)

        # 汇总
        n_kb_projects = session.query(KbProject).filter(KbProject.user_id == user.id).count()
        n_kb_skills = session.query(KbSkill).filter(KbSkill.user_id == user.id).count()
        n_kb_high = session.query(KbHighlight).filter(KbHighlight.user_id == user.id).count()
        n_kb_exp = session.query(KbExperience).filter(KbExperience.user_id == user.id).count()
        n_wiki = session.query(WikiCache).count()
        n_wiki_proj = session.query(WikiProject).count()
        n_wiki_high = session.query(WikiHighlight).count()
        print("\n===== 导入结果汇总 =====")
        print(f"kb_projects: {n_kb_projects}")
        print(f"kb_skills:   {n_kb_skills}")
        print(f"kb_high:     {n_kb_high}")
        print(f"kb_exp:      {n_kb_exp}")
        print(f"wiki_cache:  {n_wiki}")
        print(f"wiki_proj:   {n_wiki_proj}")
        print(f"wiki_high:   {n_wiki_high}")
        print("========================")
    finally:
        session.close()


if __name__ == "__main__":
    main()
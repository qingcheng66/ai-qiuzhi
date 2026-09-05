"""AI 服务：JD 结构化 + 简历生成 + 兜底"""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.llm import LLMClient, get_client
from app.services import knowledge_service, wiki_service

SYS_STRUCTURIZE = (
    "你是简历生成系统的 JD 分析器。把用户提供的招聘 JD 提取为结构化 JSON，"
    "key 必须为：company, title, skills_required(数组), responsibilities(数组), description_summary。"
    "只输出合法 JSON，不要多余文字。"
)

SYS_GENERATE = (
    "你是专业的简历撰写助手。根据给定的 JD 和候选人的真实经历数据，生成针对该 JD 优化的结构化简历。"
    "规则：\n"
    "1. 优先使用候选人提供的真实数据(projects/experience/highlights/skills)，只做针对 JD 的改写与排序，"
    "   不虚构人物、公司、项目或指标；不存在的技能不要编造。\n"
    "2. 项目与经历按与 JD 相关度排序，最相关的放最前。\n"
    "3. skills 数组每个元素含 name(归类名) 与 keywords(堆叠的具体技能词)。\n"
    "4. 若候选人数据为空，则基于 JD 生成合理的参考简历内容，并在 meta.ai_generated=true。\n"
    "输出 JSON, 结构为：{basics:{...}, education:[...], skills:[{name,keywords}...], "
    "projects:[{name,description,highlights[],meta:{targeted:true}}...], experience:[{company,role,startDate,endDate,highlights[]}...], "
    "highlights:[{title,category,content}...], meta:{target_job,ai_generated}}。只输出 JSON。"
)

SYS_REGENERATE_SECTION = (
    "你是简历撰写助手。用户正在逐段编辑简历，请只生成指定段的内容。"
    "规则：\n"
    "1. 严格只输出该段的 JSON 结构，不要包含其他段。\n"
    "2. 根据 JD 要求和已存在的简历内容，只改写目标段。\n"
    "3. 不虚构信息。\n"
    "4. 直接输出 JSON 值（不是包裹在 {section: ...} 中），只输出合法 JSON。\n"
)


def structurize_jd(client: LLMClient, text: str) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": SYS_STRUCTURIZE},
        {"role": "user", "content": text[:8000]},
    ]
    data = client.chat_json(messages)
    return {
        "company": data.get("company", ""),
        "title": data.get("title", ""),
        "skills_required": data.get("skills_required", []) or [],
        "responsibilities": data.get("responsibilities", []) or [],
        "description_summary": data.get("description_summary", "") or text[:300],
    }


def generate_resume(
    client: LLMClient,
    jd_structured: dict[str, Any],
    matches: list[dict],
    profile: dict[str, Any] | None = None,
    fallback: bool = False,
) -> dict[str, Any]:
    """生成简历。fallback=True 时不依赖匹配数据，纯 AI 参考生成。"""
    kb_ctx = json.dumps(
        {"profile": profile or {}, "matched_data": [] if fallback else matches},
        ensure_ascii=False,
    )
    jd_ctx = json.dumps(jd_structured, ensure_ascii=False)
    user_prompt = (
        "【目标 JD】\n" + jd_ctx + "\n\n【候选人真实数据】\n" + kb_ctx + "\n\n请生成针对性简历 JSON。"
    )
    messages = [
        {"role": "system", "content": SYS_GENERATE},
        {"role": "user", "content": user_prompt},
    ]
    data = client.chat_json(messages)
    data["meta"] = {
        **data.get("meta", {}),
        "ai_generated": True,
        "fallback": fallback,
        "provider": "mock" if client.is_mock() else "llm",
        "target_job": jd_structured.get("title", ""),
        "target_company": jd_structured.get("company", ""),
    }
    return data


def run_generation_pipeline(
    session: Session,
    user_id: int,
    jd: str,
) -> dict[str, Any]:
    """完整流程：结构化 → 双源匹配 → AI 生成（匹配数据空则走兜底）"""
    client = get_client()

    jd_structured = structurize_jd(client, jd)
    skills = jd_structured.get("skills_required", []) or []
    job_title = jd_structured.get("title", "")

    match_result = wiki_service.dual_match(session, user_id, skills, job_title, limit=8)
    matches = match_result["matches"]
    used_source = match_result["used_source"]

    profile = knowledge_service.get_profile(session, user_id)
    fallback = not matches
    resume = generate_resume(client, jd_structured, matches, profile, fallback=fallback)

    # 兜底：把知识库个人信息合并进 basics（除非 AI 已给）
    if profile and profile.get("name") and not resume.get("basics", {}).get("name"):
        resume.setdefault("basics", {}).update(
            {k: v for k, v in profile.items() if v and k != "education"}
        )
        if profile.get("education"):
            resume["education"] = resume.get("education") or profile["education"]

    return {
        "jd_structured": jd_structured,
        "matches": matches,
        "used_source": used_source,
        "resume": resume,
    }


def generate_tailored_reference(
    session: Session,
    user_id: int,
    jd: str,
    selected_materials: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """结合用户勾选的知识库素材与目标 JD，生成针对性参考简历"""
    client = get_client()
    jd_structured = structurize_jd(client, jd)

    if selected_materials:
        matches = selected_materials
        used_source = "user_selected_kb"
    else:
        skills = jd_structured.get("skills_required", []) or []
        job_title = jd_structured.get("title", "")
        match_result = wiki_service.dual_match(session, user_id, skills, job_title, limit=8)
        matches = match_result["matches"]
        used_source = match_result["used_source"]

    profile = knowledge_service.get_profile(session, user_id)
    fallback = not matches
    resume = generate_resume(client, jd_structured, matches, profile, fallback=fallback)

    if profile and profile.get("name") and not resume.get("basics", {}).get("name"):
        resume.setdefault("basics", {}).update(
            {k: v for k, v in profile.items() if v and k != "education"}
        )
        if profile.get("education"):
            resume["education"] = resume.get("education") or profile["education"]

    return {
        "jd_structured": jd_structured,
        "matches": matches,
        "used_source": used_source,
        "resume": resume,
    }


def regenerate_section(
    session: Session,
    user_id: int,
    section_name: str,
    jd: str,
    jd_structured: dict[str, Any] | None = None,
    matches: list[dict] | None = None,
    existing_content: dict[str, Any] | None = None,
) -> Any:
    """AI 重新生成简历的单个段。"""
    client = get_client()

    if jd_structured is None:
        jd_structured = structurize_jd(client, jd)

    if matches is None:
        skills = jd_structured.get("skills_required", []) or []
        job_title = jd_structured.get("title", "")
        match_result = wiki_service.dual_match(session, user_id, skills, job_title, limit=8)
        matches = match_result["matches"]

    profile = knowledge_service.get_profile(session, user_id)
    existing = existing_content or {}
    existing_str = json.dumps(existing, ensure_ascii=False)[:2000]
    jd_str = json.dumps(jd_structured, ensure_ascii=False)

    section_prompts = {
        "basics": "【基本信息】输出格式: {name, label, email, phone, location, url}。不存在的字段留空字符串。",
        "education": "【教育背景】输出 JSON 数组，每项含 {institution, area, studyType, gpa, startDate, endDate}。",
        "skills": "【技能清单】输出 JSON 数组，每项含 {name(分类名), keywords(技能词数组)}。",
        "projects": "【项目经验】输出 JSON 数组，每项含 {name, description, highlights[], url, meta:{targeted:bool}}。",
        "experience": "【工作经历】输出 JSON 数组，每项含 {company, role, startDate, endDate, highlights[]}。",
        "highlights": "【个人亮点】输出 JSON 数组，每项含 {title, category, content}。",
    }

    prompt = section_prompts.get(section_name)
    if not prompt:
        raise ValueError(f"不支持的段: {section_name}")

    user_prompt = (
        f"【目标 JD】\n{jd_str}\n\n"
        f"【候选人信息】\n{json.dumps({'profile': profile or {}}, ensure_ascii=False)}\n\n"
        f"【已存在的完整简历（仅参考，只改写{section_name}段）】\n{existing_str}\n\n"
        f"{prompt}\n\n"
        f"请只输出 {section_name} 段的 JSON 值。"
    )
    messages = [
        {"role": "system", "content": SYS_REGENERATE_SECTION},
        {"role": "user", "content": user_prompt},
    ]
    return client.chat_json(messages)
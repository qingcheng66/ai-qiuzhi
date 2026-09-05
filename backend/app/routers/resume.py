"""简历路由：生成 / 更新 / 导出 / 快照"""
import copy
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Position
from app.models.resume import ResumeData, ResumeVersion
from app.models.template import Template
from app.schemas.resume import (
    AiGenerateRequest,
    CreateDraftRequest,
    ExportRequest,
    FinalizeRequest,
    LinkPositionRequest,
    ResumeDataOut,
    ResumeGenerateRequest,
    ResumeSectionOut,
    ResumeUpdate,
    ResumeVersionOut,
    SectionRegenerateRequest,
    SectionUpdateRequest,
)
from app.services import ai_service, export_service

router = APIRouter(prefix="/api/resume", tags=["resume"])

SECTION_NAMES = ["basics", "education", "skills", "projects", "experience", "highlights"]


@router.post("/create-draft")
def create_draft(req: CreateDraftRequest, user_id: int = 1, db: Session = Depends(get_db)):
    # 仅当没有传入 initial_content (即为 None) 时，才从知识库中获取默认 profile
    # 若前端显式传入了 initial_content（例如新建空白简历传 {}），则保留空白
    if req.initial_content is None:
        from app.services import knowledge_service
        prof = knowledge_service.get_profile(db, user_id)
        if prof:
            init_content = {
                "basics": {
                    "name": prof.get("name", ""),
                    "label": prof.get("label", ""),
                    "email": prof.get("email", ""),
                    "phone": prof.get("phone", ""),
                    "location": prof.get("location", ""),
                    "github": prof.get("github", ""),
                    "blog": prof.get("blog", ""),
                    "summary": prof.get("summary", ""),
                    "custom_fields": [],
                },
                "education": prof.get("education", []),
                "skills": [],
                "projects": [],
                "experience": [],
                "highlights": [],
                "custom_sections": [],
            }
        else:
            init_content = {}
    else:
        init_content = req.initial_content

    draft = ResumeData(
        user_id=user_id,
        title=req.title,
        template_id=req.template_id,
        content=init_content,
        source="ai_assisted",
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return ResumeDataOut.model_validate(draft)


@router.get("/by-position/{position_id}")
def get_resume_by_position(position_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    r = (
        db.query(ResumeData)
        .filter(ResumeData.position_id == position_id, ResumeData.user_id == user_id)
        .order_by(ResumeData.updated_at.desc())
        .first()
    )
    if not r:
        return None
    return ResumeDataOut.model_validate(r)


@router.get("/", response_model=list[ResumeDataOut])
def list_resumes(user_id: int = 1, db: Session = Depends(get_db)):
    return db.query(ResumeData).filter(ResumeData.user_id == user_id).order_by(ResumeData.created_at.desc()).all()


@router.post("/generate")
def generate(req: ResumeGenerateRequest, db: Session = Depends(get_db)):
    user_id = req.user_id or 1
    if not req.jd.strip():
        raise HTTPException(status_code=400, detail="JD 文本不能为空")
    result = ai_service.run_generation_pipeline(db, user_id, req.jd)
    resume = result["resume"]
    draft = ResumeData(
        user_id=user_id,
        title=f"{result['jd_structured'].get('title', '未命名')} 简历草稿",
        content=resume,
        source="generate",
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    result["resume_id"] = draft.id
    return result


@router.post("/{resume_id}/ai-generate")
def ai_generate(resume_id: int, req: AiGenerateRequest, user_id: int = 1, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    if not req.jd.strip():
        raise HTTPException(status_code=400, detail="JD 文本不能为空")

    result = ai_service.run_generation_pipeline(db, user_id, req.jd)
    resume = result["resume"]

    r.content = resume
    r.title = f"{result['jd_structured'].get('title', '未命名')} 简历草稿"
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)

    return {
        **result,
        "resume_id": resume_id,
        "resume": resume,
    }


class GenerateReferenceRequest(BaseModel):
    jd: str
    selected_materials: list[dict] = []


@router.post("/{resume_id}/generate-reference")
def generate_reference(
    resume_id: int,
    req: GenerateReferenceRequest,
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    """根据绑定的 JD 与挑选的知识库素材，生成定向 AI 参考简历，不直接覆盖用户编辑中的主草稿"""
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    if not req.jd.strip():
        raise HTTPException(status_code=400, detail="JD 文本不能为空")

    result = ai_service.generate_tailored_reference(
        db, user_id, req.jd, req.selected_materials
    )

    # 同时也把当前 JD 保存到简历元数据，方便随时调出
    if r.content:
        content = dict(r.content)
        content["bound_jd"] = req.jd
        content["bound_jd_structured"] = result.get("jd_structured")
        r.content = content
        r.updated_at = datetime.utcnow()
        db.commit()

    return {
        **result,
        "resume_id": resume_id,
    }


@router.put("/{resume_id}/section/{section_name}")
def update_section(
    resume_id: int,
    section_name: str,
    req: SectionUpdateRequest,
    db: Session = Depends(get_db),
):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")

    content = dict(r.content) if r.content else {}
    content[section_name] = req.content
    r.content = content
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    all_sections = list(dict.fromkeys(SECTION_NAMES + list(content.keys())))
    return ResumeSectionOut(section=section_name, content=req.content, section_names=all_sections)


@router.post("/{resume_id}/regenerate-section/{section_name}")
def regenerate_section(
    resume_id: int,
    section_name: str,
    req: SectionRegenerateRequest,
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    if section_name not in SECTION_NAMES:
        raise HTTPException(status_code=400, detail=f"不支持的段: {section_name}，可选: {SECTION_NAMES}")
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    if not req.jd.strip():
        raise HTTPException(status_code=400, detail="JD 文本不能为空")

    content = dict(r.content) if r.content else {}
    new_content = ai_service.regenerate_section(
        db, user_id, section_name, req.jd,
        jd_structured=req.jd_structured,
        matches=req.matches,
        existing_content=content,
    )
    content[section_name] = new_content
    r.content = content
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return ResumeSectionOut(section=section_name, content=new_content, section_names=SECTION_NAMES)


@router.post("/{resume_id}/link-position")
def link_position(resume_id: int, req: LinkPositionRequest, user_id: int = 1, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")

    pos = db.get(Position, req.position_id)
    if not pos or pos.user_id != user_id:
        raise HTTPException(status_code=404, detail="岗位不存在")

    r.position_id = req.position_id
    db.commit()
    db.refresh(r)
    return ResumeDataOut.model_validate(r)


@router.post("/{resume_id}/finalize")
def finalize_resume(resume_id: int, req: FinalizeRequest = FinalizeRequest(), user_id: int = 1, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")

    r.status = "final"
    r.updated_at = datetime.utcnow()

    # 如果尚未关联岗位，但绑定了目标 JD，自动在求职工作台中建立企业、岗位与投递记录
    if not r.position_id and isinstance(r.content, dict) and r.content.get("target_jd", {}).get("structured"):
        st = r.content["target_jd"]["structured"]
        comp_name = st.get("company") or "目标企业"
        pos_title = st.get("title") or r.title or "目标岗位"
        from app.models.company import Company, Position, Application
        comp = db.query(Company).filter(Company.name == comp_name, Company.user_id == user_id).first()
        if not comp:
            comp = Company(user_id=user_id, name=comp_name, industry=st.get("industry") or "科技/互联网")
            db.add(comp)
            db.flush()
        pos = db.query(Position).filter(Position.company_id == comp.id, Position.title == pos_title).first()
        if not pos:
            pos = Position(
                company_id=comp.id,
                title=pos_title,
                jd_raw=r.content["target_jd"].get("raw") or "",
                jd_structured=st,
            )
            db.add(pos)
            db.flush()
        r.position_id = pos.id
        app = db.query(Application).filter(Application.position_id == pos.id, Application.user_id == user_id).first()
        if not app:
            app = Application(user_id=user_id, position_id=pos.id, stage="投递", status="active")
            db.add(app)
            db.flush()

    # 如果有关联岗位，找出投递记录并生成版本快照
    if r.position_id:
        from app.models.company import Application
        applications = (
            db.query(Application)
            .filter(Application.position_id == r.position_id, Application.user_id == user_id)
            .all()
        )
        for a in applications:
            last = (
                db.query(ResumeVersion)
                .filter(ResumeVersion.application_id == a.id)
                .order_by(ResumeVersion.version.desc())
                .first()
            )
            ver = (last.version + 1) if last else 1
            db.add(
                ResumeVersion(
                    application_id=a.id,
                    resume_data_id=resume_id,
                    version=ver,
                    change_log=req.change_log or f"v{ver}",
                    content=r.content,
                )
            )

    db.commit()
    db.refresh(r)
    return ResumeDataOut.model_validate(r)


@router.get("/{resume_id}/versions", response_model=list[ResumeVersionOut])
def list_versions(resume_id: int, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    if not r.position_id:
        return []
    from app.models.company import Application
    applications = (
        db.query(Application)
        .filter(Application.position_id == r.position_id)
        .all()
    )
    app_ids = [a.id for a in applications]
    if not app_ids:
        return []
    return (
        db.query(ResumeVersion)
        .filter(ResumeVersion.application_id.in_(app_ids))
        .order_by(ResumeVersion.version.desc())
        .all()
    )


@router.get("/{resume_id}", response_model=ResumeDataOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    return r


@router.put("/{resume_id}")
def update_resume(resume_id: int, req: ResumeUpdate, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    if req.title is not None:
        r.title = req.title
    if req.content is not None:
        r.content = req.content
    if req.template_id is not None:
        r.template_id = req.template_id
    if req.position_id is not None:
        r.position_id = req.position_id if req.position_id > 0 else None
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{resume_id}")
def delete_resume(resume_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    db.delete(r)
    db.commit()
    return {"status": "ok", "deleted_id": resume_id}


@router.post("/{resume_id}/export")
def export_resume(resume_id: int, req: ExportRequest, db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    template = None
    tid = req.template_id or r.template_id
    if tid:
        template = db.get(Template, tid)

    fmt = req.format
    if fmt == "html":
        html, tpl_name = export_service.render_html(r.content, template)
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="resume-{resume_id}.html"'},
        )
    if fmt == "pdf":
        pdf = export_service.export_pdf(r.content, template)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="resume-{resume_id}.pdf"'},
        )
    if fmt == "docx":
        docx = export_service.export_docx(r.content, template)
        return Response(
            content=docx,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="resume-{resume_id}.docx"'},
        )
    raise HTTPException(status_code=400, detail="不支持的格式")


@router.post("/{resume_id}/versions")
def snapshot_resume(resume_id: int, application_id: int, change_log: str = "", db: Session = Depends(get_db)):
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    last = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.application_id == application_id)
        .order_by(ResumeVersion.version.desc())
        .first()
    )
    ver = (last.version + 1) if last else 1
    db.add(
        ResumeVersion(
            application_id=application_id,
            resume_data_id=resume_id,
            version=ver,
            change_log=change_log or f"v{ver}",
            content=r.content,
        )
    )
    db.commit()
    return {"version": ver}


@router.post("/{resume_id}/mock-interview")
def generate_mock_interview(resume_id: int, db: Session = Depends(get_db)):
    """结合当前这份简历版本内容与其关联的 JD，生成面试官必问的 10 个高频挖掘题与回答提示"""
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    # 提取关键信息
    basics = r.content.get("basics", {})
    name = basics.get("name", "求职者")
    label = basics.get("label", "候选人")
    projects = r.content.get("projects", [])
    skills = r.content.get("skills", [])
    
    proj_names = [p.get("name") for p in projects if p.get("name")]
    skill_names = [s.get("name") for s in skills if s.get("name")]
    
    # 岗位名称
    pos_title = label or "全栈研发专家"
    if r.position_id:
        pos = db.get(Position, r.position_id)
        if pos and pos.title:
            pos_title = pos.title
        
    # 生成 5~8 道深度模拟面试挖掘问题
    questions = [
        {
            "category": "项目深挖",
            "question": f"在「{proj_names[0] if proj_names else '最近的核心项目'}」中，你负责的核心模块是什么？遇到的最大性能或设计瓶颈是什么？如何解决的？",
            "star_hint": "采用 STAR 法则：清晰说明项目背景、指标压力（如并发数或响应延迟）、你独立做出的选型决策与优化后的具体提升数据。"
        },
        {
            "category": "技术深度",
            "question": f"你在简历中多次强调了对「{skill_names[0] if skill_names else '核心技术栈'}」的熟练运用，能否深入讲讲它的底层实现原理或一次避坑排错经历？",
            "star_hint": "不要泛泛回答语法，重点展开源码层机制、内存管理或高频死锁/内存泄漏的排查工具链。"
        },
        {
            "category": "岗位匹配度",
            "question": f"针对我们「{pos_title}」岗位的工作要求，你认为自己最核心的不可替代竞争壁垒是什么？",
            "star_hint": "结合自己实战落地的代表作，对比同级别候选人，突出工程落地能力、快速业务理解与自主解决问题韧性。"
        },
        {
            "category": "团队协作与复盘",
            "question": "如果在当前简历版本的研发过程中，产品需求频繁变更或上线时间被压缩一半，你通常如何做技术权衡（Trade-off）？",
            "star_hint": "说明 MVP 最小可行方案划分、技术债务记录机制、以及与产品及跨团队的主动沟通策略。"
        }
    ]
    
    if len(proj_names) > 1:
        questions.append({
            "category": "架构与技术选型",
            "question": f"对比「{proj_names[0]}」与「{proj_names[1]}」，在技术选型和架构设计上有何不同考量？如果有机会重构，你会做什么优化？",
            "star_hint": "展现技术演进视野与反思复盘能力，说明随着业务规模变化选型的变化原因。"
        })

    return {
        "resume_id": resume_id,
        "position_title": pos_title,
        "questions": questions
    }


@router.get("/{resume_id}/stage")
def get_resume_stage(resume_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    """获取该简历绑定的求职阶段"""
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    stage_idx = r.content.get("current_stage", 0)
    from app.core import stages
    return {
        "resume_id": resume_id,
        "current_stage": stage_idx,
        "stage_name": stages.STAGES[stage_idx] if 0 <= stage_idx < len(stages.STAGES) else "未开始",
        "stages": stages.STAGES,
    }


class ResumeStageAdvanceRequest(BaseModel):
    target_stage: int


@router.post("/{resume_id}/stage")
def set_resume_stage(resume_id: int, req: ResumeStageAdvanceRequest, user_id: int = 1, db: Session = Depends(get_db)):
    """手动推进或切换该简历所处的 10 阶段求职进展"""
    r = db.get(ResumeData, resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    from app.core import stages
    target = max(0, min(req.target_stage, len(stages.STAGES) - 1))
    
    # 持久化更新到 resume_data.content
    content = dict(r.content or {})
    content["current_stage"] = target
    r.content = content
    r.updated_at = datetime.utcnow()

    # 如果关联了 Application，也同步推进 Application 的 current_stage
    if r.position_id:
        from app.models.company import Application
        apps = db.query(Application).filter(Application.position_id == r.position_id, Application.user_id == user_id).all()
        for a in apps:
            a.current_stage = target

    db.commit()
    return {
        "resume_id": resume_id,
        "current_stage": target,
        "stage_name": stages.STAGES[target],
    }
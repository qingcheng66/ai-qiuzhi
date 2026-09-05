"""应用内知识库路由：profile/projects/skills/highlights/experiences CRUD + 导入"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.knowledge import (
    KbExperience,
    KbHighlight,
    KbProfile,
    KbProject,
    KbSkill,
)
from app.schemas.knowledge import (
    KbBundle,
    KbExperienceIn,
    KbExperienceOut,
    KbHighlightIn,
    KbHighlightOut,
    KbProfileIn,
    KbProfileOut,
    KbProjectIn,
    KbProjectOut,
    KbSkillIn,
    KbSkillOut,
    KbSortUpdate,
    KbToggleUpdate,
)
from app.services import knowledge_service

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


def _uid(user_id: int | None) -> int:
    return user_id or 1


# ---------- bundle ----------


@router.get("/bundle", response_model=KbBundle)
def bundle(user_id: int = 1, db: Session = Depends(get_db)):
    data = knowledge_service.get_bundle(db, user_id)
    # 需要把 ORM 对象转纯 dict（避免 pydantic from_attributes 混用问题）
    def _row(obj):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    return KbBundle(
        profile=data["profile"],
        projects=[_row(x) for x in data["projects"]],
        skills=[_row(x) for x in data["skills"]],
        highlights=[_row(x) for x in data["highlights"]],
        experiences=[_row(x) for x in data["experiences"]],
        categories=data.get("categories", []),
    )


# ---------- v2 categories & chunks ----------

from app.models.knowledge import KbCategory, KbChunk
from app.schemas.knowledge import KbCategoryIn, KbCategoryOut, KbChunkIn, KbChunkOut


@router.post("/categories", response_model=KbCategoryOut)
def create_category(req: KbCategoryIn, user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)
    cat = KbCategory(
        user_id=uid,
        name=req.name,
        icon=req.icon or "folder",
        color=req.color or "blue",
        sort_order=req.sort_order,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return KbCategoryOut(
        id=cat.id,
        user_id=cat.user_id,
        name=cat.name,
        icon=cat.icon,
        color=cat.color,
        sort_order=cat.sort_order,
        chunks=[],
    )


@router.put("/categories/{category_id}", response_model=KbCategoryOut)
def update_category(category_id: int, req: KbCategoryIn, user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)
    cat = db.get(KbCategory, category_id)
    if not cat or cat.user_id != uid:
        raise HTTPException(status_code=404, detail="栏目不存在")
    cat.name = req.name
    cat.icon = req.icon
    cat.color = req.color
    cat.sort_order = req.sort_order
    db.commit()
    db.refresh(cat)
    chunks = db.scalars(
        select(KbChunk).where(KbChunk.category_id == cat.id).order_by(KbChunk.sort_order)
    ).all()
    return KbCategoryOut(
        id=cat.id,
        user_id=cat.user_id,
        name=cat.name,
        icon=cat.icon,
        color=cat.color,
        sort_order=cat.sort_order,
        chunks=[
            KbChunkOut(
                id=c.id,
                user_id=c.user_id,
                category_id=c.category_id,
                title=c.title,
                content=c.content,
                tags=c.tags or [],
                enabled=c.enabled,
                sort_order=c.sort_order,
                created_at=c.created_at.isoformat() if c.created_at else None,
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
            )
            for c in chunks
        ],
    )


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)
    cat = db.get(KbCategory, category_id)
    if not cat or cat.user_id != uid:
        raise HTTPException(status_code=404, detail="栏目不存在")
    db.delete(cat)
    db.commit()
    return {"deleted": category_id}


@router.post("/categories/{category_id}/chunks", response_model=KbChunkOut)
def create_chunk(category_id: int, req: KbChunkIn, user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)
    cat = db.get(KbCategory, category_id)
    if not cat or cat.user_id != uid:
        raise HTTPException(status_code=404, detail="栏目不存在")
    chunk = KbChunk(
        user_id=uid,
        category_id=category_id,
        title=req.title,
        content=req.content,
        tags=req.tags,
        enabled=req.enabled,
        sort_order=req.sort_order,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return KbChunkOut(
        id=chunk.id,
        user_id=chunk.user_id,
        category_id=chunk.category_id,
        title=chunk.title,
        content=chunk.content,
        tags=chunk.tags or [],
        enabled=chunk.enabled,
        sort_order=chunk.sort_order,
        created_at=chunk.created_at.isoformat() if chunk.created_at else None,
        updated_at=chunk.updated_at.isoformat() if chunk.updated_at else None,
    )


@router.put("/chunks/{chunk_id}", response_model=KbChunkOut)
def update_chunk(chunk_id: int, req: KbChunkIn, user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)
    chunk = db.get(KbChunk, chunk_id)
    if not chunk or chunk.user_id != uid:
        raise HTTPException(status_code=404, detail="卡片不存在")
    chunk.title = req.title
    chunk.content = req.content
    chunk.tags = req.tags
    chunk.enabled = req.enabled
    chunk.sort_order = req.sort_order
    db.commit()
    db.refresh(chunk)
    return KbChunkOut(
        id=chunk.id,
        user_id=chunk.user_id,
        category_id=chunk.category_id,
        title=chunk.title,
        content=chunk.content,
        tags=chunk.tags or [],
        enabled=chunk.enabled,
        sort_order=chunk.sort_order,
        created_at=chunk.created_at.isoformat() if chunk.created_at else None,
        updated_at=chunk.updated_at.isoformat() if chunk.updated_at else None,
    )


@router.delete("/chunks/{chunk_id}")
def delete_chunk(chunk_id: int, user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)
    chunk = db.get(KbChunk, chunk_id)
    if not chunk or chunk.user_id != uid:
        raise HTTPException(status_code=404, detail="卡片不存在")
    db.delete(chunk)
    db.commit()
    return {"deleted": chunk_id}


@router.patch("/chunks/{chunk_id}/toggle")
def toggle_chunk(chunk_id: int, req: KbToggleUpdate, user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)
    chunk = db.get(KbChunk, chunk_id)
    if not chunk or chunk.user_id != uid:
        raise HTTPException(status_code=404, detail="卡片不存在")
    chunk.enabled = req.enabled
    db.commit()
    return {"id": chunk_id, "enabled": chunk.enabled}



# ---------- profile ----------


@router.get("/profile", response_model=KbProfileOut | None)
def get_profile(user_id: int = 1, db: Session = Depends(get_db)):
    p = db.scalars(select(KbProfile).where(KbProfile.user_id == user_id)).first()
    return p


@router.put("/profile", response_model=KbProfileOut)
def upsert_profile(req: KbProfileIn, user_id: int = 1, db: Session = Depends(get_db)):
    p = knowledge_service.upsert_profile(db, _uid(user_id), req.model_dump())
    return p


# ---------- projects ----------


def _ensure(db: Session, model, pk: int, uid: int):
    obj = db.get(model, pk)
    if not obj or obj.user_id != uid:
        raise HTTPException(status_code=404, detail="记录不存在")
    return obj


@router.get("/projects", response_model=list[KbProjectOut])
def list_projects(user_id: int = 1, db: Session = Depends(get_db)):
    return db.scalars(
        select(KbProject)
        .where(KbProject.user_id == user_id)
        .order_by(KbProject.sort_order, KbProject.id)
    ).all()


@router.post("/projects", response_model=KbProjectOut)
def create_project(req: KbProjectIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = KbProject(user_id=_uid(user_id), **req.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.put("/projects/{pk}", response_model=KbProjectOut)
def update_project(pk: int, req: KbProjectIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbProject, pk, _uid(user_id))
    for k, v in req.model_dump().items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/projects/{pk}")
def delete_project(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbProject, pk, _uid(user_id))
    db.delete(o)
    db.commit()
    return {"deleted": pk}


@router.patch("/projects/{pk}/enabled")
def toggle_project(pk: int, req: KbToggleUpdate, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbProject, pk, _uid(user_id))
    o.enabled = req.enabled
    db.commit()
    return {"id": pk, "enabled": o.enabled}


# ---------- skills ----------


@router.get("/skills", response_model=list[KbSkillOut])
def list_skills(user_id: int = 1, db: Session = Depends(get_db)):
    return db.scalars(
        select(KbSkill).where(KbSkill.user_id == user_id).order_by(KbSkill.sort_order, KbSkill.id)
    ).all()


@router.post("/skills", response_model=KbSkillOut)
def create_skill(req: KbSkillIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = KbSkill(user_id=_uid(user_id), **req.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.put("/skills/{pk}", response_model=KbSkillOut)
def update_skill(pk: int, req: KbSkillIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbSkill, pk, _uid(user_id))
    for k, v in req.model_dump().items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/skills/{pk}")
def delete_skill(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbSkill, pk, _uid(user_id))
    db.delete(o)
    db.commit()
    return {"deleted": pk}


# ---------- highlights ----------


@router.get("/highlights", response_model=list[KbHighlightOut])
def list_highlights(user_id: int = 1, db: Session = Depends(get_db)):
    return db.scalars(
        select(KbHighlight)
        .where(KbHighlight.user_id == user_id)
        .order_by(KbHighlight.sort_order, KbHighlight.id)
    ).all()


@router.post("/highlights", response_model=KbHighlightOut)
def create_highlight(req: KbHighlightIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = KbHighlight(user_id=_uid(user_id), **req.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.put("/highlights/{pk}", response_model=KbHighlightOut)
def update_highlight(pk: int, req: KbHighlightIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbHighlight, pk, _uid(user_id))
    for k, v in req.model_dump().items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/highlights/{pk}")
def delete_highlight(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbHighlight, pk, _uid(user_id))
    db.delete(o)
    db.commit()
    return {"deleted": pk}


# ---------- experiences ----------


@router.get("/experiences", response_model=list[KbExperienceOut])
def list_experiences(user_id: int = 1, db: Session = Depends(get_db)):
    return db.scalars(
        select(KbExperience)
        .where(KbExperience.user_id == user_id)
        .order_by(KbExperience.sort_order, KbExperience.id)
    ).all()


@router.post("/experiences", response_model=KbExperienceOut)
def create_experience(req: KbExperienceIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = KbExperience(user_id=_uid(user_id), **req.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.put("/experiences/{pk}", response_model=KbExperienceOut)
def update_experience(pk: int, req: KbExperienceIn, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbExperience, pk, _uid(user_id))
    for k, v in req.model_dump().items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/experiences/{pk}")
def delete_experience(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure(db, KbExperience, pk, _uid(user_id))
    db.delete(o)
    db.commit()
    return {"deleted": pk}


# ---------- 通用排序 / 导入 ----------


@router.post("/reorder")
def reorder(items: list[KbSortUpdate], kind: str = "project", user_id: int = 1, db: Session = Depends(get_db)):
    model = {
        "project": KbProject,
        "skill": KbSkill,
        "highlight": KbHighlight,
        "experience": KbExperience,
    }.get(kind)
    if not model:
        raise HTTPException(status_code=400, detail="kind 无效")
    for it in items:
        o = db.get(model, it.id)
        if o and o.user_id == _uid(user_id):
            o.sort_order = it.sort_order
    db.commit()
    return {"reordered": len(items)}


class KBImportRequest(BaseModel):
    content: str
    user_id: int | None = None


@router.post("/import")
def import_kb(
    req: KBImportRequest,
    db: Session = Depends(get_db),
):
    """导入知识库数据。content 为 JSON 字符串（JSON Resume 或本应用结构）。"""
    uid = _uid(req.user_id)
    if not req.content:
        raise HTTPException(status_code=400, detail="content 不能为空")
    data = knowledge_service.parse_import_text(req.content)
    if data is None:
        raise HTTPException(status_code=400, detail="无法解析 JSON")
    counts = knowledge_service.import_kb_from_json(db, uid, data)
    return {"counts": counts}


@router.post("/import/file")
async def import_kb_file(file: UploadFile = File(...), user_id: int | None = None, db: Session = Depends(get_db)):
    raw = (await file.read()).decode("utf-8")
    data = knowledge_service.parse_import_text(raw)
    if data is None:
        raise HTTPException(status_code=400, detail="无法解析 JSON")
    counts = knowledge_service.import_kb_from_json(db, _uid(user_id), data)
    return {"counts": counts}
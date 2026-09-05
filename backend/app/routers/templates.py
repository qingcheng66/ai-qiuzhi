"""模板路由：CRUD + 预览渲染 + PDF/Word 导入解析（P3）"""
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.template import Template
from app.schemas.template import (
    TemplateCreate,
    TemplateOut,
    TemplateRenderRequest,
    TemplateUpdate,
)
from app.services import export_service, template_service

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _uid(user_id: int | None) -> int:
    return user_id or 1


@router.get("/", response_model=list[TemplateOut])
def list_templates(user_id: int = 1, db: Session = Depends(get_db)):
    return (
        db.query(Template)
        .filter((Template.user_id == user_id) | (Template.is_builtin.is_(True)))
        .order_by(Template.is_builtin.desc(), Template.id)
        .all()
    )


@router.post("/", response_model=TemplateOut)
def create_template(req: TemplateCreate, user_id: int = 1, db: Session = Depends(get_db)):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="模板内容不能为空")
    o = Template(
        user_id=_uid(user_id),
        name=req.name,
        description=req.description,
        type=req.type or "custom",
        source="html",
        content=req.content,
        variables=req.variables,
        is_builtin=False,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.get("/{pk}", response_model=TemplateOut)
def get_template(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = db.get(Template, pk)
    if not o:
        raise HTTPException(status_code=404, detail="模板不存在")
    return o


@router.put("/{pk}", response_model=TemplateOut)
def update_template(pk: int, req: TemplateUpdate, user_id: int = 1, db: Session = Depends(get_db)):
    o = db.get(Template, pk)
    if not o:
        raise HTTPException(status_code=404, detail="模板不存在")
    for k, v in req.model_dump().items():
        if v is not None:
            setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/{pk}")
def delete_template(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = db.get(Template, pk)
    if not o or (o.is_builtin and o.user_id != _uid(user_id)):
        raise HTTPException(status_code=404, detail="模板不存在")
    db.delete(o)
    db.commit()
    return {"deleted": pk}


@router.post("/{pk}/render")
def render_template(pk: int, req: TemplateRenderRequest, user_id: int = 1, db: Session = Depends(get_db)):
    o = db.get(Template, pk)
    if not o:
        raise HTTPException(status_code=404, detail="模板不存在")
    html, _ = export_service.render_html(req.content, o)
    return {"html": html}


@router.post("/import")
async def import_template(file: UploadFile = File(...), name: str = "", user_id: int | None = None, db: Session = Depends(get_db)):
    """导入 PDF/DOCX 为模板，生成可复用的 Jinja2 HTML（基于原始布局的骨架）"""
    if not name:
        name = Path(file.filename or "imported").stem
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .pdf / .docx")

    raw = await file.read()
    if ext == ".pdf":
        html = template_service.pdf_to_template(raw)
        source = "pdf"
    else:
        html = template_service.docx_to_template(raw)
        source = "docx"

    o = Template(
        user_id=_uid(user_id),
        name=name,
        description=f"从 {file.filename or 'file'} 导入",
        type="custom",
        source=source,
        content=html,
        variables=template_service.extract_variables(html),
        is_builtin=False,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o
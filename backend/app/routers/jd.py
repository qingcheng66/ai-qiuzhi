"""JD 相关路由：文本/OCR 结果 → LLM 结构化"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.wiki import JDStructured, StructurizeRequest
from app.services import ai_service

router = APIRouter(prefix="/api/jd", tags=["jd"])


@router.post("/structurize", response_model=JDStructured)
def structurize(req: StructurizeRequest):
    if not req.text.strip():
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="JD 文本不能为空")
    data = ai_service.structurize_jd(ai_service.get_client(), req.text)
    return JDStructured(**data)
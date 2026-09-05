"""Wiki/知识库匹配路由：JD 技能关键词 → 双源匹配（kb + wiki）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.wiki import WikiMatchRequest, WikiMatchResponse
from app.services import wiki_service

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.post("/match", response_model=WikiMatchResponse)
def match(req: WikiMatchRequest, db: Session = Depends(get_db)):
    user_id = req.user_id or 1
    if not req.skills:
        raise HTTPException(status_code=400, detail="skills 不能为空")
    result = wiki_service.dual_match(db, user_id, req.skills, req.job_title, limit=req.limit)
    return WikiMatchResponse(
        matches=result["matches"],
        used_source=result["used_source"],
    )
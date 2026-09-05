from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import user as user_schemas
from app.services import ocr_service

"""OCR 路由：解析图片文字。
未配置 API Key 时返回明确提示，前端降级为粘贴文本。
"""


def get_default_user_id() -> int:
    return 1


router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/parse")
async def parse(
    file: UploadFile = File(...),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片上传")
    image_bytes = await file.read()
    try:
        text = ocr_service.ocr_image_bytes(image_bytes)
        return {"text": text, "provider": ocr_service.get_ocr_provider().name}
    except ocr_service.OCRUnavailable as e:
        raise HTTPException(status_code=501, detail=str(e))
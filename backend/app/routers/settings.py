from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import setting_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMConfigPayload(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@router.get("/llm")
def get_llm_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    """获取当前配置的大模型提供商及可用列表"""
    return setting_service.get_llm_config_view(db)


@router.post("/llm")
def save_llm_settings(
    payload: LLMConfigPayload, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """保存用户输入的模型提供商与 API Key"""
    return setting_service.save_llm_config(db, payload.model_dump())


@router.post("/llm/test")
def test_llm_settings(
    payload: LLMConfigPayload, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """测试指定模型提供商与 API Key 连通性"""
    return setting_service.test_llm_connection(db, payload.model_dump())


class SwitchPayload(BaseModel):
    provider: str


@router.post("/llm/switch")
def switch_llm_provider(
    payload: SwitchPayload, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """像 CC-Switch 一样快速切换当前激活的模型提供商"""
    return setting_service.switch_active_provider(db, payload.provider)


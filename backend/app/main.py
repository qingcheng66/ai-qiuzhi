from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_all
from app.routers import jd, kb, ocr, resume, settings as settings_router, templates, wiki, workspace
from app.services import export_service

app = FastAPI(title="ai-qiuzhi", version="1.0.0", description="AI 求职辅助工具 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.resolved_cors(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_all()
    export_service.load_builtin_templates()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "llm": settings.llm_provider}


# 注册路由
app.include_router(ocr.router)
app.include_router(jd.router)
app.include_router(wiki.router)
app.include_router(resume.router)
app.include_router(kb.router)
app.include_router(workspace.router)
app.include_router(templates.router)
app.include_router(settings_router.router)
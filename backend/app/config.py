from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ai-qiuzhi"
    debug: bool = True

    # 数据库（SQLite 开发 / PostgreSQL 生产，切换 DATABASE_URL 即可）
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'ai-qiuzhi.db'}"

    # LLM 多供应商（DeepSeek / OpenRouter，均 OpenAI 兼容）
    llm_provider: str = "mock"  # deepseek | openrouter | mock
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    llm_mock: bool = False  # 显式强制 mock，即使配了 key

    # OCR - MinerU 文档解析（优先）
    mineru_ocr_token: str = ""
    mineru_ocr_model: str = "vlm"  # pipeline / vlm / MinerU-HTML
    mineru_ocr_timeout: int = 180

    # OCR（百度/腾讯），未配置时路由降级返回提示
    baidu_ocr_api_key: str = ""
    baidu_ocr_secret_key: str = ""
    tencent_ocr_secret_id: str = ""
    tencent_ocr_secret_key: str = ""

    # 前端开发服务器地址（CORS）
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    def resolved_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
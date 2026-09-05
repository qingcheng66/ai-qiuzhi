import json
import time
from typing import Any
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.setting import SystemSetting

SUPPORTED_PROVIDERS = {
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek (深度求索)",
        "icon": "🐳",
        "description": "高性价比推理与代码能力，国内直连高速稳定推荐",
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "available_models": ["deepseek-chat", "deepseek-reasoner"],
        "key_placeholder": "sk-...",
        "docs_url": "https://platform.deepseek.com/api_keys",
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI (GPT-4o)",
        "icon": "⚡",
        "description": "官方 OpenAI 接口，支持 GPT-4o / GPT-4o-mini 等全系模型",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "available_models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "key_placeholder": "sk-proj-...",
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "zhipu": {
        "id": "zhipu",
        "name": "智谱清言 GLM (Zhipu AI)",
        "icon": "🔮",
        "description": "清华智谱开放平台 GLM-4 旗舰系列，国内直连响应极快",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "available_models": ["glm-4-flash", "glm-4-plus", "glm-4-air"],
        "key_placeholder": "例如: 3e8a...xxx",
        "docs_url": "https://open.bigmodel.cn/usercenter/apikeys",
    },
    "moonshot": {
        "id": "moonshot",
        "name": "月之暗面 Kimi (Moonshot)",
        "icon": "🌙",
        "description": "擅长超长上下文精准解析与多轮润色分析",
        "default_base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "available_models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "key_placeholder": "sk-...",
        "docs_url": "https://platform.moonshot.cn/console/api-keys",
    },
    "qwen": {
        "id": "qwen",
        "name": "通义千问 Qwen (阿里云百炼)",
        "icon": "☁️",
        "description": "阿里百炼大模型平台，官方兼容 OpenAI 接口规范",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "available_models": ["qwen-plus", "qwen-turbo", "qwen-max"],
        "key_placeholder": "sk-...",
        "docs_url": "https://bailian.console.aliyun.com/?apiKey=1",
    },
    "siliconflow": {
        "id": "siliconflow",
        "name": "硅基流动 SiliconFlow",
        "icon": "🚀",
        "description": "聚合开源顶尖大模型（支持 DeepSeek V3 / R1 等）的高速中继平台",
        "default_base_url": "https://api.siliconflow.cn/v1",
        "default_model": "deepseek-ai/DeepSeek-V3",
        "available_models": [
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct",
        ],
        "key_placeholder": "sk-...",
        "docs_url": "https://cloud.siliconflow.cn/account/ak",
    },
    "openrouter": {
        "id": "openrouter",
        "name": "OpenRouter",
        "icon": "🌐",
        "description": "全球模型聚合网关，支持一个 Key 调用全球主流模型",
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "deepseek/deepseek-chat",
        "available_models": [
            "deepseek/deepseek-chat",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-haiku",
        ],
        "key_placeholder": "sk-or-...",
        "docs_url": "https://openrouter.ai/keys",
    },
    "custom": {
        "id": "custom",
        "name": "自定义 OpenAI 兼容接口",
        "icon": "🛠️",
        "description": "支持 Ollama、OneAPI、NewAPI、vLLM 等任意兼容 OpenAI 协议的自建服务",
        "default_base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5:latest",
        "available_models": [],
        "key_placeholder": "自定义服务的 API Key（如无需校验可填任意字符）",
        "docs_url": "",
    },
}

LLM_CONFIG_KEY = "llm_config"


def mask_api_key(key: str | None) -> str:
    if not key:
        return ""
    key = str(key).strip()
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


def is_masked(key: str | None) -> bool:
    if not key:
        return False
    return "****" in key


def get_raw_llm_config(db: Session) -> dict[str, Any]:
    """获取数据库或环境变量中的原始配置（包含未遮盖的 API Key）"""
    record = db.get(SystemSetting, LLM_CONFIG_KEY)
    if record and record.value:
        try:
            cfg = json.loads(record.value)
            if isinstance(cfg, dict) and cfg.get("provider"):
                return cfg
        except Exception:
            pass

    # 兜底从环境变量 settings 中读取旧版 deepseek / openrouter 配置
    provider = settings.llm_provider if settings.llm_provider in SUPPORTED_PROVIDERS else "deepseek"
    if provider == "deepseek" and settings.deepseek_api_key:
        return {
            "provider": "deepseek",
            "api_key": settings.deepseek_api_key,
            "base_url": settings.deepseek_base_url or "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
        }
    elif provider == "openrouter" and settings.openrouter_api_key:
        return {
            "provider": "openrouter",
            "api_key": settings.openrouter_api_key,
            "base_url": settings.openrouter_base_url or "https://openrouter.ai/api/v1",
            "model": "deepseek/deepseek-v4-flash",
        }

    # 默认空白配置
    p_info = SUPPORTED_PROVIDERS.get("deepseek", {})
    return {
        "provider": "deepseek",
        "api_key": "",
        "base_url": p_info.get("default_base_url", "https://api.deepseek.com/v1"),
        "model": p_info.get("default_model", "deepseek-chat"),
    }


def get_llm_config_view(db: Session) -> dict[str, Any]:
    """返回用于前端展示的配置（API Key 已脱敏安全处理）及可用提供商列表"""
    raw = get_raw_llm_config(db)
    provider_id = raw.get("provider", "deepseek")
    p_info = SUPPORTED_PROVIDERS.get(provider_id, SUPPORTED_PROVIDERS["deepseek"])

    return {
        "current": {
            "provider": provider_id,
            "api_key_masked": mask_api_key(raw.get("api_key", "")),
            "has_key": bool(raw.get("api_key", "").strip()),
            "base_url": raw.get("base_url") or p_info.get("default_base_url", ""),
            "model": raw.get("model") or p_info.get("default_model", ""),
        },
        "providers": list(SUPPORTED_PROVIDERS.values()),
    }


def save_llm_config(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """保存用户输入的 LLM 配置（支持提供商切换与 API Key 自动持久化）"""
    provider_id = data.get("provider", "deepseek")
    p_info = SUPPORTED_PROVIDERS.get(provider_id, SUPPORTED_PROVIDERS["custom"])

    new_key = (data.get("api_key") or "").strip()
    base_url = (data.get("base_url") or "").strip() or p_info.get("default_base_url", "")
    model = (data.get("model") or "").strip() or p_info.get("default_model", "")

    # 处理遮罩 Key：若用户未修改（仍为 sk-****abcd），则保留库中现有 Key
    if is_masked(new_key):
        old_raw = get_raw_llm_config(db)
        if old_raw.get("provider") == provider_id and old_raw.get("api_key"):
            new_key = old_raw["api_key"]
        else:
            new_key = ""

    config_to_save = {
        "provider": provider_id,
        "api_key": new_key,
        "base_url": base_url,
        "model": model,
    }

    record = db.get(SystemSetting, LLM_CONFIG_KEY)
    if not record:
        record = SystemSetting(key=LLM_CONFIG_KEY, value=json.dumps(config_to_save, ensure_ascii=False))
        db.add(record)
    else:
        record.value = json.dumps(config_to_save, ensure_ascii=False)
    db.commit()

    # 重置 LLM 客户端单例，使后续请求即刻生效
    from app.core import llm
    llm.reset_client()

    return get_llm_config_view(db)


def test_llm_connection(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """测试指定 LLM 供应商连通性与 API Key 有效性"""
    provider_id = data.get("provider", "deepseek")
    p_info = SUPPORTED_PROVIDERS.get(provider_id, SUPPORTED_PROVIDERS["custom"])

    input_key = (data.get("api_key") or "").strip()
    base_url = (data.get("base_url") or "").strip() or p_info.get("default_base_url", "")
    model = (data.get("model") or "").strip() or p_info.get("default_model", "")

    # 如果传入的是遮盖后的 key，从数据库获取真实 key
    if is_masked(input_key):
        raw = get_raw_llm_config(db)
        input_key = raw.get("api_key", "").strip()

    if not input_key:
        return {
            "success": False,
            "latency_ms": 0,
            "message": "请先输入 API Key 再进行测试！",
        }

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {input_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a health-check bot. Answer only 'OK'."},
            {"role": "user", "content": "ping"},
        ],
        "max_tokens": 10,
        "temperature": 0.1,
    }

    start_t = time.perf_counter()
    try:
        with httpx.Client(timeout=15.0, transport=httpx.HTTPTransport(proxy=None)) as client:
            resp = client.post(url, headers=headers, json=body)
            elapsed = time.perf_counter() - start_t
            latency_ms = int(elapsed * 1000)

            if resp.status_code == 200:
                res_json = resp.json()
                reply = res_json["choices"][0]["message"]["content"].strip()
                return {
                    "success": True,
                    "latency_ms": latency_ms,
                    "reply": reply,
                    "message": f"连接成功！模型 [{model}] 响应正常，往返延迟 {latency_ms} ms",
                }
            else:
                err_body = resp.text[:300]
                return {
                    "success": False,
                    "latency_ms": latency_ms,
                    "status_code": resp.status_code,
                    "message": f"连接失败 (HTTP {resp.status_code}): {err_body}",
                }
    except httpx.ConnectTimeout:
        return {
            "success": False,
            "latency_ms": 0,
            "message": f"连接超时 (15s)，请检查 Base URL [{base_url}] 是否正确或网络是否畅通",
        }
    except httpx.ConnectError as e:
        return {
            "success": False,
            "latency_ms": 0,
            "message": f"网络连接错误，无法访问 [{base_url}]: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "latency_ms": 0,
            "message": f"测试异常: {str(e)}",
        }

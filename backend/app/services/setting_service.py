import json
import time
from typing import Any
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.setting import SystemSetting

SUPPORTED_PROVIDERS = {
    # ======= 国内主流大厂 =======
    "deepseek": {
        "id": "deepseek",
        "category": "domestic",
        "name": "DeepSeek (深度求索)",
        "icon": "🐳",
        "badge": "超高性价比",
        "description": "顶尖推理与代码逻辑能力，官方提供高性价比 API，国内直连高速稳定首选",
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "available_models": ["deepseek-chat", "deepseek-reasoner"],
        "key_placeholder": "sk-...",
        "docs_url": "https://platform.deepseek.com/api_keys",
    },
    "zhipu": {
        "id": "zhipu",
        "category": "domestic",
        "name": "智谱清言 GLM (Zhipu AI)",
        "icon": "🔮",
        "badge": "免费体验额度",
        "description": "清华智谱 GLM-4 系列模型，国内直连毫秒级响应，glm-4-flash 超轻量免费高效",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "available_models": ["glm-4-flash", "glm-4-plus", "glm-4-air", "glm-4-long"],
        "key_placeholder": "例如: 3e8a...xxx",
        "docs_url": "https://open.bigmodel.cn/usercenter/apikeys",
    },
    "moonshot": {
        "id": "moonshot",
        "category": "domestic",
        "name": "月之暗面 Kimi (Moonshot)",
        "icon": "🌙",
        "badge": "超长上下文",
        "description": "国内长文本先驱，对复杂职位 JD 与候选人经历的深度理解与润色尤为出色",
        "default_base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "available_models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-latest"],
        "key_placeholder": "sk-...",
        "docs_url": "https://platform.moonshot.cn/console/api-keys",
    },
    "qwen": {
        "id": "qwen",
        "category": "domestic",
        "name": "通义千问 Qwen (阿里云百炼)",
        "icon": "☁️",
        "badge": "大厂稳定保障",
        "description": "阿里巴巴百炼大模型平台，官方全兼容 OpenAI 接口规范，综合泛化能力极强",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "available_models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen2.5-72b-instruct"],
        "key_placeholder": "sk-...",
        "docs_url": "https://bailian.console.aliyun.com/?apiKey=1",
    },
    "doubao": {
        "id": "doubao",
        "category": "domestic",
        "name": "字节跳动 豆包 (火山引擎 Ark)",
        "icon": "🥟",
        "badge": "字节自研",
        "description": "火山引擎大模型服务平台，支持 Doubao-pro-32k 与 Doubao-lite 高并发低延迟调用",
        "default_base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-1.5-pro-32k",
        "available_models": ["doubao-1.5-pro-32k", "doubao-pro-32k", "doubao-lite-32k"],
        "key_placeholder": "例如: 7b2c...（火山引擎 API Key）",
        "docs_url": "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey",
    },
    "qianfan": {
        "id": "qianfan",
        "category": "domestic",
        "name": "百度千帆文心 (Baidu Qianfan)",
        "icon": "🐻",
        "badge": "文心一言",
        "description": "百度千帆大模型平台官方兼容端点，支持 ERNIE-4.0 与 ERNIE-Speed 等系列",
        "default_base_url": "https://qianfan.baidubce.com/v2",
        "default_model": "ernie-4.0-turbo-8k",
        "available_models": ["ernie-4.0-turbo-8k", "ernie-3.5-8k", "ernie-speed-128k"],
        "key_placeholder": "bce-v3/...（千帆平台 API Key）",
        "docs_url": "https://console.bce.baidu.com/qianfan/ais/console/onlineService",
    },
    "minimax": {
        "id": "minimax",
        "category": "domestic",
        "name": "MiniMax (海螺 AI / 名之梦)",
        "icon": "🐚",
        "badge": "多模态与文案",
        "description": "自研 MoE 架构 Text-01 与 abab6.5 系列大模型，文本润色与拟人化表达优秀",
        "default_base_url": "https://api.minimax.chat/v1",
        "default_model": "MiniMax-Text-01",
        "available_models": ["MiniMax-Text-01", "abab6.5s-chat", "abab6.5-chat"],
        "key_placeholder": "sk-api-...（MiniMax API Key）",
        "docs_url": "https://platform.minimaxi.com/user-center/basic-information/interface-key",
    },
    "lingyi": {
        "id": "lingyi",
        "category": "domestic",
        "name": "零一万物 01.AI (李开复 Yi)",
        "icon": "💡",
        "badge": "闪电极速",
        "description": "支持 Yi-Lightning 旗舰模型，极低延迟与极具竞争力的推理性能",
        "default_base_url": "https://api.lingyiwanwu.com/v1",
        "default_model": "yi-lightning",
        "available_models": ["yi-lightning", "yi-large", "yi-medium"],
        "key_placeholder": "sk-...（零一万物 API Key）",
        "docs_url": "https://platform.lingyiwanwu.com/apikeys",
    },
    "baichuan": {
        "id": "baichuan",
        "category": "domestic",
        "name": "百川智能 Baichuan",
        "icon": "🌊",
        "badge": "知识增强",
        "description": "自研 Baichuan4 知识密集型大模型，针对中文政企与招聘专业领域表现优异",
        "default_base_url": "https://api.baichuan-ai.com/v1",
        "default_model": "Baichuan4",
        "available_models": ["Baichuan4", "Baichuan3-Turbo", "Baichuan2-Turbo"],
        "key_placeholder": "sk-...",
        "docs_url": "https://platform.baichuan-ai.com/console/apikey",
    },
    "stepfun": {
        "id": "stepfun",
        "category": "domestic",
        "name": "阶跃星辰 StepFun (跃问)",
        "icon": "🪐",
        "badge": "万亿参数",
        "description": "万亿参数 MoE 架构 Step-1 系列模型，中文语境与复杂指令遵循优异",
        "default_base_url": "https://api.stepfun.com/v1",
        "default_model": "step-1-8k",
        "available_models": ["step-1-8k", "step-1-32k", "step-1-flash"],
        "key_placeholder": "step-...",
        "docs_url": "https://platform.stepfun.com/interface-key",
    },

    # ======= 国际顶尖模型 =======
    "openai": {
        "id": "openai",
        "category": "global",
        "name": "OpenAI (ChatGPT)",
        "icon": "⚡",
        "badge": "行业基准",
        "description": "官方 OpenAI 接口，支持 GPT-4o / GPT-4o-mini / o1-mini 等全系模型",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "available_models": ["gpt-4o-mini", "gpt-4o", "o1-mini", "gpt-3.5-turbo"],
        "key_placeholder": "sk-proj-...",
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "id": "gemini",
        "category": "global",
        "name": "Google Gemini",
        "icon": "✨",
        "badge": "Google 旗舰",
        "description": "Google 官方兼容端点，支持极速响应的 Gemini 2.0 Flash 与 1.5 Pro",
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "available_models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "key_placeholder": "AIzaSy...（Google AI Studio Key）",
        "docs_url": "https://aistudio.google.com/app/apikey",
    },
    "groq": {
        "id": "groq",
        "category": "global",
        "name": "Groq (LPU 极速推理)",
        "icon": "⚡",
        "badge": "全球最快",
        "description": "独家 LPU 架构，推理速度达数百 token/s，支持 Llama-3.3 与 DeepSeek R1 蒸馏",
        "default_base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "available_models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "deepseek-r1-distill-llama-70b"],
        "key_placeholder": "gsk_...",
        "docs_url": "https://console.groq.com/keys",
    },
    "mistral": {
        "id": "mistral",
        "category": "global",
        "name": "Mistral AI",
        "icon": "🌪️",
        "badge": "欧洲之星",
        "description": "欧洲开源与商用模型领头羊，支持 Mistral-Small / Large 与 Codestral",
        "default_base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
        "available_models": ["mistral-small-latest", "mistral-large-latest", "codestral-latest"],
        "key_placeholder": "sk-...（Mistral Console Key）",
        "docs_url": "https://console.mistral.ai/api-keys/",
    },
    "perplexity": {
        "id": "perplexity",
        "category": "global",
        "name": "Perplexity AI",
        "icon": "🔍",
        "badge": "搜索增强",
        "description": "擅长结合实时互联网信息的 Sonar 系列模型，针对最新岗位行情感知敏锐",
        "default_base_url": "https://api.perplexity.ai",
        "default_model": "sonar-pro",
        "available_models": ["sonar-pro", "sonar"],
        "key_placeholder": "pplx-...",
        "docs_url": "https://www.perplexity.ai/settings/api",
    },

    # ======= 算力聚合平台 =======
    "siliconflow": {
        "id": "siliconflow",
        "category": "aggregator",
        "name": "硅基流动 SiliconFlow",
        "icon": "🚀",
        "badge": "开源模型聚合",
        "description": "国内聚合顶尖开源大模型的高速中继平台，满血版 DeepSeek V3 / R1 稳定直连",
        "default_base_url": "https://api.siliconflow.cn/v1",
        "default_model": "deepseek-ai/DeepSeek-V3",
        "available_models": [
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct",
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
        ],
        "key_placeholder": "sk-...",
        "docs_url": "https://cloud.siliconflow.cn/account/ak",
    },
    "openrouter": {
        "id": "openrouter",
        "category": "aggregator",
        "name": "OpenRouter",
        "icon": "🌐",
        "badge": "全球网关",
        "description": "全球模型聚合网关，支持一个 Key 自由调用 Claude 3.5、GPT-4o、DeepSeek 等",
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "deepseek/deepseek-chat",
        "available_models": [
            "deepseek/deepseek-chat",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-haiku",
            "google/gemini-2.0-flash-exp:free",
        ],
        "key_placeholder": "sk-or-...",
        "docs_url": "https://openrouter.ai/keys",
    },

    # ======= 本地私有化与自建代理 =======
    "ollama": {
        "id": "ollama",
        "category": "local_custom",
        "name": "Ollama (本地私有部署)",
        "icon": "🦙",
        "badge": "100% 本地离线",
        "description": "运行在您本地电脑上的 Ollama 服务，无需互联网即可离线运行开源模型，完全免费且隐私",
        "default_base_url": "http://localhost:11434/v1",
        "default_model": "deepseek-r1:latest",
        "available_models": ["deepseek-r1:latest", "qwen2.5:latest", "llama3.2:latest"],
        "key_placeholder": "ollama（本地无需 API Key，填任意字符即可）",
        "docs_url": "https://ollama.com/",
    },
    "custom": {
        "id": "custom",
        "category": "local_custom",
        "name": "自定义 OpenAI 兼容接口",
        "icon": "🛠️",
        "badge": "任意兼容反代",
        "description": "支持 OneAPI、NewAPI、vLLM、FastChat 等任意兼容 OpenAI 协议的自建或中转服务",
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

    # Ollama 或本地无需强校验 key
    if not input_key and provider_id not in ("ollama", "custom"):
        return {
            "success": False,
            "latency_ms": 0,
            "message": "请先输入 API Key 再进行测试！",
        }

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {input_key or 'test'}",
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

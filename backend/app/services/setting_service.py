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
        "available_models": [
            {"id": "deepseek-chat", "label": "deepseek-chat (DeepSeek-V3，推荐)"},
            {"id": "deepseek-reasoner", "label": "deepseek-reasoner (DeepSeek-R1 深度推理)"},
        ],
        "key_placeholder": "sk-...",
        "docs_url": "https://platform.deepseek.com/api_keys",
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
        "available_models": [
            {"id": "moonshot-v1-8k", "label": "moonshot-v1-8k (8K 上下文，推荐)"},
            {"id": "moonshot-v1-32k", "label": "moonshot-v1-32k (32K 长文本)"},
            {"id": "moonshot-v1-128k", "label": "moonshot-v1-128k (128K 超长文)"},
            {"id": "kimi-latest", "label": "kimi-latest (最新 Kimi 模型)"},
        ],
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
        "available_models": [
            {"id": "qwen-plus", "label": "qwen-plus (性能与成本平衡，推荐)"},
            {"id": "qwen-turbo", "label": "qwen-turbo (高速极简版)"},
            {"id": "qwen-max", "label": "qwen-max (千亿级超强旗舰)"},
            {"id": "qwen2.5-72b-instruct", "label": "qwen2.5-72b-instruct (开源顶峰)"},
        ],
        "key_placeholder": "sk-...",
        "docs_url": "https://bailian.console.aliyun.com/?apiKey=1",
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
        "available_models": [
            {"id": "glm-4-flash", "label": "glm-4-flash (超快且免费，推荐)"},
            {"id": "glm-4-plus", "label": "glm-4-plus (高智能旗舰版)"},
            {"id": "glm-4-air", "label": "glm-4-air (轻量平衡版)"},
            {"id": "glm-4-long", "label": "glm-4-long (百万上下文)"},
        ],
        "key_placeholder": "例如: 3e8a...xxx",
        "docs_url": "https://open.bigmodel.cn/usercenter/apikeys",
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
        "available_models": [
            {"id": "doubao-1.5-pro-32k", "label": "doubao-1.5-pro-32k (新一代主力，推荐)"},
            {"id": "doubao-pro-32k", "label": "doubao-pro-32k (综合专业版)"},
            {"id": "doubao-lite-32k", "label": "doubao-lite-32k (极速低成本版)"},
        ],
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
        "available_models": [
            {"id": "ernie-4.0-turbo-8k", "label": "ernie-4.0-turbo-8k (文心 4.0 旗舰，推荐)"},
            {"id": "ernie-3.5-8k", "label": "ernie-3.5-8k (文心 3.5 主流版)"},
            {"id": "ernie-speed-128k", "label": "ernie-speed-128k (千帆免费极速长文)"},
        ],
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
        "available_models": [
            {"id": "MiniMax-Text-01", "label": "MiniMax-Text-01 (自研 MoE 旗舰，推荐)"},
            {"id": "abab6.5s-chat", "label": "abab6.5s-chat (高响应速度)"},
            {"id": "abab6.5-chat", "label": "abab6.5-chat (完整能力版)"},
        ],
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
        "available_models": [
            {"id": "yi-lightning", "label": "yi-lightning (闪电旗舰模型，推荐)"},
            {"id": "yi-large", "label": "yi-large (深度推理大模型)"},
            {"id": "yi-medium", "label": "yi-medium (高性价比中型版)"},
        ],
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
        "available_models": [
            {"id": "Baichuan4", "label": "Baichuan4 (百川第四代旗舰，推荐)"},
            {"id": "Baichuan3-Turbo", "label": "Baichuan3-Turbo (高通量加速版)"},
        ],
        "key_placeholder": "sk-...（百川 API Key）",
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
        "available_models": [
            {"id": "step-1-8k", "label": "step-1-8k (主力基座模型，推荐)"},
            {"id": "step-1-32k", "label": "step-1-32k (32K 上下文扩展)"},
            {"id": "step-1-flash", "label": "step-1-flash (极速体验版)"},
        ],
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
        "available_models": [
            {"id": "gpt-4o-mini", "label": "gpt-4o-mini (极佳速度与性价比，推荐)"},
            {"id": "gpt-4o", "label": "gpt-4o (完整全能多模态旗舰)"},
            {"id": "o1-mini", "label": "o1-mini (强化思维链推理)"},
            {"id": "gpt-3.5-turbo", "label": "gpt-3.5-turbo (经典通用版)"},
        ],
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
        "available_models": [
            {"id": "gemini-2.0-flash", "label": "gemini-2.0-flash (次世代超快闪电模型，推荐)"},
            {"id": "gemini-1.5-flash", "label": "gemini-1.5-flash (高效百万上下文)"},
            {"id": "gemini-1.5-pro", "label": "gemini-1.5-pro (深度通用旗舰)"},
        ],
        "key_placeholder": "AIzaSy...（Google AI Studio Key）",
        "docs_url": "https://aistudio.google.com/app/apikey",
    },
    "groq": {
        "id": "groq",
        "category": "global",
        "name": "Groq (LPU 极速推理)",
        "icon": "⚡",
        "badge": "全球最快",
        "description": "独家 LPU 硬件芯片架构，推理速度达数百 token/s，支持 Llama-3.3 与 DeepSeek R1 蒸馏",
        "default_base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "available_models": [
            {"id": "llama-3.3-70b-versatile", "label": "llama-3.3-70b-versatile (最新 70B 顶峰，推荐)"},
            {"id": "llama-3.1-8b-instant", "label": "llama-3.1-8b-instant (毫秒级输出)"},
            {"id": "deepseek-r1-distill-llama-70b", "label": "deepseek-r1-distill-llama-70b (DeepSeek 蒸馏版)"},
        ],
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
        "available_models": [
            {"id": "mistral-small-latest", "label": "mistral-small-latest (小巧强悍，推荐)"},
            {"id": "mistral-large-latest", "label": "mistral-large-latest (顶级推理旗舰)"},
            {"id": "codestral-latest", "label": "codestral-latest (代码强化专业版)"},
        ],
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
        "available_models": [
            {"id": "sonar-pro", "label": "sonar-pro (搜索增强专业版)"},
            {"id": "sonar", "label": "sonar (标准搜索对话版)"},
        ],
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
            {"id": "deepseek-ai/DeepSeek-V3", "label": "deepseek-ai/DeepSeek-V3 (满血 671B，推荐)"},
            {"id": "deepseek-ai/DeepSeek-R1", "label": "deepseek-ai/DeepSeek-R1 (深度思考版)"},
            {"id": "Qwen/Qwen2.5-72B-Instruct", "label": "Qwen/Qwen2.5-72B-Instruct (通义千问开源版)"},
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
            {"id": "deepseek/deepseek-chat", "label": "deepseek/deepseek-chat (超高性价比推荐)"},
            {"id": "openai/gpt-4o-mini", "label": "openai/gpt-4o-mini"},
            {"id": "anthropic/claude-3.5-haiku", "label": "anthropic/claude-3.5-haiku"},
            {"id": "google/gemini-2.0-flash-exp:free", "label": "google/gemini-2.0-flash-exp:free (免费版)"},
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
        "available_models": [
            {"id": "deepseek-r1:latest", "label": "deepseek-r1:latest (本地 R1 模型)"},
            {"id": "qwen2.5:latest", "label": "qwen2.5:latest (本地千问)"},
            {"id": "llama3.2:latest", "label": "llama3.2:latest (本地 Llama 3.2)"},
        ],
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
            if isinstance(cfg, dict):
                # 新版支持 saved_configs 结构
                if "active" in cfg and isinstance(cfg["active"], dict):
                    return cfg
                elif cfg.get("provider"):
                    return {
                        "active": cfg,
                        "saved_configs": {cfg["provider"]: cfg},
                    }
        except Exception:
            pass

    # 兜底从环境变量 settings 中读取
    provider = settings.llm_provider if settings.llm_provider in SUPPORTED_PROVIDERS else "deepseek"
    init_cfg = {
        "provider": provider,
        "api_key": settings.deepseek_api_key if provider == "deepseek" else (settings.openrouter_api_key if provider == "openrouter" else ""),
        "base_url": settings.deepseek_base_url if provider == "deepseek" else (settings.openrouter_base_url if provider == "openrouter" else "https://api.deepseek.com/v1"),
        "model": "deepseek-chat" if provider == "deepseek" else "deepseek/deepseek-v4-flash",
    }
    return {
        "active": init_cfg,
        "saved_configs": {provider: init_cfg} if init_cfg["api_key"] else {},
    }


def get_llm_config_view(db: Session) -> dict[str, Any]:
    """返回用于前端展示的视图：当前激活模型、已保存的提供商预设、全部可用模型库"""
    raw = get_raw_llm_config(db)
    active = raw.get("active", {})
    provider_id = active.get("provider", "deepseek")
    p_info = SUPPORTED_PROVIDERS.get(provider_id, SUPPORTED_PROVIDERS["deepseek"])

    saved_raw = raw.get("saved_configs", {})
    saved_list = []
    for pid, c in saved_raw.items():
        if pid in SUPPORTED_PROVIDERS and c.get("api_key"):
            meta = SUPPORTED_PROVIDERS[pid]
            saved_list.append({
                "provider": pid,
                "name": meta["name"],
                "icon": meta["icon"],
                "model": c.get("model", meta["default_model"]),
                "api_key_masked": mask_api_key(c.get("api_key", "")),
                "is_active": (pid == provider_id),
            })

    return {
        "current": {
            "provider": provider_id,
            "api_key_masked": mask_api_key(active.get("api_key", "")),
            "has_key": bool(active.get("api_key", "").strip()) or provider_id in ("ollama", "custom"),
            "base_url": active.get("base_url") or p_info.get("default_base_url", ""),
            "model": active.get("model") or p_info.get("default_model", ""),
        },
        "saved_configs": saved_list,
        "providers": list(SUPPORTED_PROVIDERS.values()),
    }


def save_llm_config(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """保存用户输入的 LLM 配置（更新当前提供商，并将该提供商写入保存库，支持像 CC Switch 一样一键热切）"""
    provider_id = data.get("provider", "deepseek")
    p_info = SUPPORTED_PROVIDERS.get(provider_id, SUPPORTED_PROVIDERS["custom"])

    new_key = (data.get("api_key") or "").strip()
    base_url = (data.get("base_url") or "").strip() or p_info.get("default_base_url", "")
    model = (data.get("model") or "").strip() or p_info.get("default_model", "")

    raw = get_raw_llm_config(db)
    saved_configs = raw.get("saved_configs", {})

    # 处理遮罩 Key：若用户未修改（仍为 sk-****abcd），保留该厂商现有 Key
    if is_masked(new_key):
        if provider_id in saved_configs and saved_configs[provider_id].get("api_key"):
            new_key = saved_configs[provider_id]["api_key"]
        elif raw.get("active", {}).get("provider") == provider_id and raw.get("active", {}).get("api_key"):
            new_key = raw["active"]["api_key"]
        else:
            new_key = ""

    current_item = {
        "provider": provider_id,
        "api_key": new_key,
        "base_url": base_url,
        "model": model,
    }

    saved_configs[provider_id] = current_item
    new_store = {
        "active": current_item,
        "saved_configs": saved_configs,
    }

    record = db.get(SystemSetting, LLM_CONFIG_KEY)
    if not record:
        record = SystemSetting(key=LLM_CONFIG_KEY, value=json.dumps(new_store, ensure_ascii=False))
        db.add(record)
    else:
        record.value = json.dumps(new_store, ensure_ascii=False)
    db.commit()

    # 重置 LLM 客户端单例，使后续请求即刻生效
    from app.core import llm
    llm.reset_client()

    return get_llm_config_view(db)


def switch_active_provider(db: Session, provider_id: str) -> dict[str, Any]:
    """像 CC-Switch 一样：在已保存的多个模型厂商之间一键快速热切换"""
    raw = get_raw_llm_config(db)
    saved_configs = raw.get("saved_configs", {})

    if provider_id in saved_configs and (saved_configs[provider_id].get("api_key") or provider_id in ("ollama", "custom")):
        raw["active"] = saved_configs[provider_id]
        record = db.get(SystemSetting, LLM_CONFIG_KEY)
        if record:
            record.value = json.dumps(raw, ensure_ascii=False)
            db.commit()

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
        saved = raw.get("saved_configs", {}).get(provider_id, {})
        input_key = saved.get("api_key") or raw.get("active", {}).get("api_key", "")

    # 本地无需强校验 key
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

"""LLM 多供应商客户端

支持 deepseek / openrouter（均 OpenAI 兼容）/ mock。
未配置任何 key 时自动降级为 MockLLMClient，保证全链路可调试。
"""
import json
import re
from typing import Any

import httpx

from app.config import settings


class _ProviderConfig:
    base_url: str
    api_key: str
    model: str


class DeepSeekConfig(_ProviderConfig):
    base_url = settings.deepseek_base_url
    api_key = settings.deepseek_api_key
    model = "deepseek-chat"


class OpenRouterConfig(_ProviderConfig):
    base_url = settings.openrouter_base_url
    api_key = settings.openrouter_api_key
    model = "deepseek/deepseek-v4-flash"


PROVIDERS = {"deepseek": DeepSeekConfig, "openrouter": OpenRouterConfig}


class LLMError(Exception):
    pass


class LLMClient:
    """统一 LLM 调用接口"""

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        raise NotImplementedError

    def chat_json(
        self, messages: list[dict], temperature: float = 0.3
    ) -> dict[str, Any]:
        """强制返回 JSON dict"""
        content = self.chat(messages, temperature=temperature)
        return extract_json(content)

    def is_mock(self) -> bool:
        return False


class RealLLMClient(LLMClient):
    def __init__(self, cfg: _ProviderConfig):
        self._cfg = cfg
        self._client = httpx.Client(timeout=120, transport=httpx.HTTPTransport(proxy=None))

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        url = f"{self._cfg.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._cfg.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._cfg.model,
            "messages": messages,
            "temperature": temperature,
        }
        try:
            resp = self._client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise LLMError(f"LLM 请求失败: {e}") from e
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise LLMError(f"LLM 响应解析失败: {e}") from e


def extract_json(text: str) -> dict[str, Any]:
    """从任意文本中提取 JSON 对象"""
    text = text.strip()
    # 尝试围栏代码块
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 截取第一个 { 到最后一个 }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise LLMError(f"无法从 LLM 响应中解析 JSON: {text[:200]}")


def get_llm_client() -> LLMClient:
    """根据配置返回可用的 LLM 客户端"""
    if not settings.llm_mock:
        for name in ("deepseek", "openrouter"):
            cfg = PROVIDERS[name]()
            if cfg.api_key and (settings.llm_provider == "mock" or settings.llm_provider == name):
                return RealLLMClient(cfg)
        for name in ("deepseek", "openrouter"):
            cfg = PROVIDERS[name]()
            if cfg.api_key:
                return RealLLMClient(cfg)
    return MockLLMClient()


_llm_cache: LLMClient | None = None


def get_client() -> LLMClient:
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = get_llm_client()
    return _llm_cache


def reset_client():
    global _llm_cache
    _llm_cache = None


class MockLLMClient(LLMClient):
    """确定性 Mock：基于规则生成结构化数据，确保无 key 也能全链路验证"""

    def is_mock(self) -> bool:
        return True

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        return self._respond(messages)

    def chat_json(
        self, messages: list[dict], temperature: float = 0.3
    ) -> dict[str, Any]:
        return extract_json(self._respond(messages))

    def _respond(self, messages: list[dict]) -> str:
        system_prompts = " ".join(
            m.get("content", "") for m in messages if m.get("role") == "system"
        )
        last = messages[-1].get("content", "") if messages else ""
        # 生成简历任务：system 提示包含 target_job（更特异，优先判断，
        # 因为其 user prompt 也会包含 JD 结构化的 skills_required）
        if "target_job" in system_prompts:
            return self._mock_resume(system_prompts)
        # 结构化任务：system 提示包含 skills_required
        if "skills_required" in system_prompts:
            return self._mock_jd(last)
        return json.dumps({"mock": True, "echo": last[:100]}, ensure_ascii=False)

    def _mock_jd(self, task: str) -> str:
        title = "前端开发工程师"
        m = re.findall(r"岗位[：:]\s*(\S+)", task)
        if m:
            title = m[0]
        keywords = re.findall(r"技能[：:]\s*([^\n]+)", task)
        skills = [k.strip() for k in keywords[0].split("、") if k.strip()] if keywords else ["Vue", "TypeScript"]
        return json.dumps(
            {
                "company": "示例公司",
                "title": title,
                "skills_required": skills,
                "responsibilities": ["负责核心功能开发", "参与需求评审与方案设计"],
                "description_summary": task[:200],
            },
            ensure_ascii=False,
        )

    def _mock_resume(self, prompt: str) -> str:
        return json.dumps(
            {
                "basics": {"name": "刘仁晓君", "label": "软件工程应届生", "email": "1120835055@qq.com"},
                "education": [
                    {"institution": "南京中医药大学", "area": "软件工程", "studyType": "本科", "gpa": "3.8", "startDate": "2023/09", "endDate": "2027/06"}
                ],
                "skills": [{"name": "AI 工程", "keywords": ["LangGraph", "RAG", "DeepSeek"]}, {"name": "后端", "keywords": ["Java Spring Boot"]}],
                "projects": [
                    {"name": "DevDoc AI", "description": "AI 文档自动生成助手", "highlights": ["LangGraph 多节点 Agent 工作流", "ChromaDB RAG 双路检索"]}
                ],
                "experience": [{"company": "上海九地之下技术有限公司", "role": "AI 全栈开发工程师", "highlights": ["并行推进 5+ 项目"]}],
                "highlights": [{"title": "高并发电商", "content": "36 万行代码支撑 2400+ 用户"}],
                "meta": {"ai_generated": True, "provider": "mock", "target_job": ""},
            },
            ensure_ascii=False,
        )
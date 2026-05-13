import json
import logging

from config import (
    EVENT_ANALYSIS_API_KEY,
    EVENT_ANALYSIS_BASE_URL,
    EVENT_ANALYSIS_MAX_INPUT_CHARS,
    EVENT_ANALYSIS_MODEL,
    EVENT_ANALYSIS_TEMPERATURE,
    EVENT_ANALYSIS_TIMEOUT,
)
from services.analysis.llm_model_config import LLMModelConfigSnapshot
from services.llm.chat import LLMChatMessage, LLMChatRequest, OpenAICompatibleChatClient

from .schemas import EventAnalysisResult, TimelinePoint
from .text_utils import natural_clip

logger = logging.getLogger(__name__)


class LLMEventAnalysisProvider:
    provider = "llm"

    def analyze(self, items, chronological_items=None, history_context: str | None = None) -> EventAnalysisResult:
        raise NotImplementedError


class OpenAICompatibleEventAnalysisProvider(LLMEventAnalysisProvider):
    """适配本地千问、vLLM、Xinference、LM Studio 等 OpenAI Compatible 接口。"""

    provider = "openai_compatible"

    def __init__(
        self,
        base_url: str = EVENT_ANALYSIS_BASE_URL,
        api_key: str = EVENT_ANALYSIS_API_KEY,
        model_name: str = EVENT_ANALYSIS_MODEL,
        timeout: int = EVENT_ANALYSIS_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self._config = LLMModelConfigSnapshot(
            id=0,
            provider_name=self.provider,
            provider_code=self.provider,
            base_url=self.base_url,
            api_key=self.api_key,
            model_name=self.model_name,
            is_enabled=1,
            daily_call_limit=0,
            daily_call_count=0,
            last_call_date=None,
            priority=100,
            consecutive_failure_count=0,
            circuit_open_until=None,
            last_failure_reason="",
        )

    def analyze(self, items, chronological_items=None, history_context: str | None = None) -> EventAnalysisResult:
        chronological_items = chronological_items or items
        prompt = self._build_prompt(items, chronological_items, history_context)
        chat_result = OpenAICompatibleChatClient(self._config).chat(
            LLMChatRequest(
                messages=[
                    LLMChatMessage(role="system", content="你是信息达人事件分析引擎，只输出严格JSON。"),
                    LLMChatMessage(role="user", content=prompt),
                ],
                temperature=EVENT_ANALYSIS_TEMPERATURE,
                response_format={"type": "json_object"},
                timeout_seconds=self.timeout,
                input_item_count=len(items),
            )
        )
        data = json.loads(chat_result.content)
        return self._parse_result(data, chronological_items)

    def _build_prompt(self, items, chronological_items, history_context: str | None = None) -> str:
        source_blocks: list[str] = []
        consumed = 0
        for index, item in enumerate(items[:8], start=1):
            content = natural_clip(item.content or "", 1800)
            block = (
                f"来源{index}\n"
                f"标题：{item.title}\n"
                f"渠道：{item.channel.name if getattr(item, 'channel', None) else item.channel_id}\n"
                f"时间：{item.event_time or item.created_at}\n"
                f"正文：{content}\n"
            )
            if consumed + len(block) > EVENT_ANALYSIS_MAX_INPUT_CHARS:
                break
            source_blocks.append(block)
            consumed += len(block)

        prompt = (
            "请基于真实来源生成事件分析，不要简单截取原文，不要编造没有证据的事实。\n"
            "输出JSON字段：one_line_summary, what_happened, why_it_matters, latest_update, "
            "heat_reason, risk_notice, source_compare, analysis_confidence, evolution_summary, history_context。\n"
            "每个字段必须是通顺中文完整句子。\n\n"
        )

        # 加入历史背景（如果有）
        if history_context:
            prompt += f"【历史背景】\n{history_context}\n\n"

        prompt += "【当前来源】\n" + "\n".join(source_blocks)
        return prompt

    def _parse_result(self, data: dict, chronological_items) -> EventAnalysisResult:
        timeline_points = [
            TimelinePoint(
                occurred_at=item.event_time or item.created_at,
                summary=natural_clip(item.content or item.title or "", 140),
                source_item_id=item.id,
                confidence=0.7,
                evidence={"title": item.title, "url": item.source_url},
            )
            for item in chronological_items
        ]

        # 收集使用的 Info ID 用于溯源
        used_info_ids = [item.id for item in chronological_items if item.id]

        return EventAnalysisResult(
            one_line_summary=str(data.get("one_line_summary", "")),
            what_happened=str(data.get("what_happened", "")),
            why_it_matters=str(data.get("why_it_matters", "")),
            latest_update=str(data.get("latest_update", "")),
            heat_reason=str(data.get("heat_reason", "")),
            risk_notice=str(data.get("risk_notice", "")),
            source_compare=str(data.get("source_compare", "")),
            analysis_confidence=str(data.get("analysis_confidence", "")),
            evolution_summary=str(data.get("evolution_summary", "")),
            history_context=str(data.get("history_context", "")),
            timeline_points=timeline_points,
            used_info_ids=used_info_ids,
            provider=self.provider,
            model_name=self.model_name,
            mode="llm",
            quality_score=80.0,
            confidence=0.78,
        )


class OllamaEventAnalysisProvider(OpenAICompatibleEventAnalysisProvider):
    provider = "ollama"


class DashScopeEventAnalysisProvider(OpenAICompatibleEventAnalysisProvider):
    provider = "dashscope"


class CustomHTTPEventAnalysisProvider(OpenAICompatibleEventAnalysisProvider):
    provider = "custom_http"


def build_llm_provider(provider: str) -> LLMEventAnalysisProvider:
    providers = {
        "openai_compatible": OpenAICompatibleEventAnalysisProvider,
        "ollama": OllamaEventAnalysisProvider,
        "dashscope": DashScopeEventAnalysisProvider,
        "custom_http": CustomHTTPEventAnalysisProvider,
    }
    provider_class = providers.get(provider, OpenAICompatibleEventAnalysisProvider)
    return provider_class()


def build_llm_provider_from_config(config) -> LLMEventAnalysisProvider:
    provider = OpenAICompatibleEventAnalysisProvider(
        base_url=config.base_url,
        api_key=config.api_key or "",
        model_name=config.model_name,
    )
    if hasattr(config, "id"):
        provider._config = LLMModelConfigSnapshot(
            id=config.id or 0,
            provider_name=getattr(config, "provider_name", "") or "",
            provider_code=getattr(config, "provider_code", "") or "openai_compatible",
            base_url=config.base_url,
            api_key=config.api_key or "",
            model_name=config.model_name,
            is_enabled=int(getattr(config, "is_enabled", 1) or 0),
            daily_call_limit=int(getattr(config, "daily_call_limit", 0) or 0),
            daily_call_count=int(getattr(config, "daily_call_count", 0) or 0),
            last_call_date=getattr(config, "last_call_date", None),
            priority=int(getattr(config, "priority", 100) or 100),
            consecutive_failure_count=int(getattr(config, "consecutive_failure_count", 0) or 0),
            circuit_open_until=getattr(config, "circuit_open_until", None),
            last_failure_reason=getattr(config, "last_failure_reason", "") or "",
        )
    provider.provider = config.provider_code or "openai_compatible"
    return provider

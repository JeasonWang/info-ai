import json
import logging

from config import (
    EVENT_ANALYSIS_API_KEY,
    EVENT_ANALYSIS_BASE_URL,
    EVENT_ANALYSIS_MODEL,
    EVENT_ANALYSIS_TEMPERATURE,
    EVENT_ANALYSIS_TIMEOUT,
)
from services.analysis.llm_model_config import LLMModelConfigSnapshot
from services.llm.chat import LLMChatMessage, LLMChatRequest, OpenAICompatibleChatClient

from .schemas import EventAnalysisResult
from .prompt_builder import EventAnalysisPromptBuilder
from .result_parser import EventAnalysisResultParser

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
        self.prompt_builder = EventAnalysisPromptBuilder()
        self.result_parser = EventAnalysisResultParser()

    def analyze(self, items, chronological_items=None, history_context: str | None = None) -> EventAnalysisResult:
        chronological_items = chronological_items or items
        prompt = self.prompt_builder.build(items, chronological_items, history_context)
        request = LLMChatRequest(
            messages=[
                LLMChatMessage(role="system", content=prompt.system_prompt),
                LLMChatMessage(role="user", content=prompt.user_prompt),
            ],
            temperature=EVENT_ANALYSIS_TEMPERATURE,
            response_format={"type": "json_object"},
            timeout_seconds=self.timeout,
            input_item_count=len(items),
            log_context={
                "source": "event_analysis",
                "prompt_version": prompt.prompt_version,
                "source_item_ids": prompt.source_item_ids,
            },
        )
        self.last_request_payload = {
            "model": self._config.model_name,
            "temperature": request.temperature,
            "response_format": request.response_format,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "context": request.log_context,
        }
        chat_result = OpenAICompatibleChatClient(self._config).chat(
            request
        )
        self.last_response_content = chat_result.content
        self.last_response_payload = chat_result.raw_response
        data = json.loads(chat_result.content)
        return self.result_parser.parse(data, chronological_items, self.provider, self.model_name)


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

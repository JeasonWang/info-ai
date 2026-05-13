import logging
import time

from config import (
    EVENT_ANALYSIS_ENABLE_LLM,
    EVENT_ANALYSIS_FALLBACK_TO_RULE,
    EVENT_ANALYSIS_LLM_RETRY_TIMES,
    EVENT_ANALYSIS_MODE,
    EVENT_ANALYSIS_PROVIDER,
)

from .providers import build_llm_provider
from .providers import build_llm_provider_from_config
from .rule_provider import RuleEventAnalysisProvider
from .schemas import EventAnalysisResult
from .validator import normalize_result
from .llm_runner import run_event_analysis_llm
from services.analysis.llm_model_config import (
    record_llm_call_failure_independent,
    record_llm_call_success_independent,
    select_available_llm_config_independent,
)

logger = logging.getLogger(__name__)


def analyze_event_sources(
    items,
    chronological_items=None,
    session=None,
    history_context: str | None = None,
) -> EventAnalysisResult:
    chronological_items = chronological_items or items
    rule_result = RuleEventAnalysisProvider().analyze(items, chronological_items, history_context=history_context)
    title = items[0].title if items else ""
    rule_result = normalize_result(rule_result, title=title)

    selected_config = select_available_llm_config_independent() if session is not None else None
    if EVENT_ANALYSIS_MODE == "rule":
        return rule_result
    if session is None and not EVENT_ANALYSIS_ENABLE_LLM:
        return rule_result
    if session is not None and selected_config is None:
        return rule_result

    try:
        provider = build_llm_provider_from_config(selected_config) if selected_config is not None else build_llm_provider(EVENT_ANALYSIS_PROVIDER)
        started_at = time.perf_counter()
        llm_result = run_event_analysis_llm(
            provider,
            items,
            chronological_items,
            history_context,
            title,
            EVENT_ANALYSIS_LLM_RETRY_TIMES,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if selected_config is not None:
            try:
                record_llm_call_success_independent(
                    selected_config.id,
                    latency_ms,
                    len(items),
                    request_payload=getattr(provider, "last_request_payload", None),
                    response_content=getattr(provider, "last_response_content", ""),
                    response_payload=getattr(provider, "last_response_payload", None),
                )
            except Exception as log_exc:
                logger.warning("事件大模型调用成功，但调用日志记录失败: %s", log_exc)
        llm_result.mode = EVENT_ANALYSIS_MODE
        return llm_result
    except Exception as exc:
        logger.warning("事件大模型分析失败，回退规则分析: %s", exc)
        if session is not None and selected_config is not None:
            latency_ms = int((time.perf_counter() - started_at) * 1000) if "started_at" in locals() else 0
            try:
                record_llm_call_failure_independent(
                    selected_config.id,
                    latency_ms,
                    len(items),
                    str(exc),
                    request_payload=getattr(provider, "last_request_payload", None) if "provider" in locals() else None,
                    response_content=getattr(provider, "last_response_content", "") if "provider" in locals() else "",
                    response_payload=getattr(provider, "last_response_payload", None) if "provider" in locals() else None,
                )
            except Exception as log_exc:
                logger.warning("事件大模型调用失败，且失败日志记录失败: %s", log_exc)
        if not EVENT_ANALYSIS_FALLBACK_TO_RULE:
            raise
        rule_result.fallback_used = True
        rule_result.failure_reason = str(exc)[:500]
        return rule_result

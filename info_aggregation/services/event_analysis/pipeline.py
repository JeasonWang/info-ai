import logging
import time

from config import (
    EVENT_ANALYSIS_ENABLE_LLM,
    EVENT_ANALYSIS_FALLBACK_TO_RULE,
    EVENT_ANALYSIS_MODE,
    EVENT_ANALYSIS_PROVIDER,
)

from .providers import build_llm_provider
from .providers import build_llm_provider_from_config
from .rule_provider import RuleEventAnalysisProvider
from .schemas import EventAnalysisResult
from .validator import normalize_result, validate_result
from services.analysis.llm_model_config import (
    record_llm_call_failure,
    record_llm_call_success,
    select_available_llm_config,
)

logger = logging.getLogger(__name__)


def analyze_event_sources(items, chronological_items=None, session=None) -> EventAnalysisResult:
    chronological_items = chronological_items or items
    rule_result = RuleEventAnalysisProvider().analyze(items, chronological_items)
    title = items[0].title if items else ""
    rule_result = normalize_result(rule_result, title=title)

    selected_config = select_available_llm_config(session) if session is not None else None
    if EVENT_ANALYSIS_MODE == "rule":
        return rule_result
    if session is None and not EVENT_ANALYSIS_ENABLE_LLM:
        return rule_result
    if session is not None and selected_config is None:
        return rule_result

    try:
        provider = build_llm_provider_from_config(selected_config) if selected_config is not None else build_llm_provider(EVENT_ANALYSIS_PROVIDER)
        started_at = time.perf_counter()
        llm_result = provider.analyze(items, chronological_items)
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        llm_result = normalize_result(llm_result, title=title)
        problems = validate_result(llm_result)
        if problems:
            raise ValueError(f"invalid_llm_result:{','.join(problems)}")
        if selected_config is not None:
            record_llm_call_success(session, selected_config, latency_ms, len(items))
        llm_result.mode = EVENT_ANALYSIS_MODE
        return llm_result
    except Exception as exc:
        logger.warning("事件大模型分析失败，回退规则分析: %s", exc)
        if session is not None and selected_config is not None:
            latency_ms = int((time.perf_counter() - started_at) * 1000) if "started_at" in locals() else 0
            record_llm_call_failure(session, selected_config, latency_ms, len(items), str(exc))
        if not EVENT_ANALYSIS_FALLBACK_TO_RULE:
            raise
        rule_result.fallback_used = True
        rule_result.failure_reason = str(exc)[:500]
        return rule_result

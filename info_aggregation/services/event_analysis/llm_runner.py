import inspect
import logging

from .validator import normalize_result, validate_result

logger = logging.getLogger(__name__)


def _provider_accepts_history_context(provider) -> bool:
    """Allow older provider doubles to keep working while newer providers accept history context."""
    try:
        signature = inspect.signature(provider.analyze)
    except (TypeError, ValueError):
        return True
    return "history_context" in signature.parameters


def _provider_accepts_tasks(provider) -> bool:
    try:
        signature = inspect.signature(provider.analyze)
    except (TypeError, ValueError):
        return True
    return "tasks" in signature.parameters


def _analyze_with_provider(provider, items, chronological_items, history_context: str | None, tasks=None):
    accepts_history = _provider_accepts_history_context(provider)
    accepts_tasks = _provider_accepts_tasks(provider)
    if accepts_history and accepts_tasks:
        return provider.analyze(items, chronological_items, history_context=history_context, tasks=tasks)
    if accepts_history:
        return provider.analyze(items, chronological_items, history_context=history_context)
    if accepts_tasks:
        return provider.analyze(items, chronological_items, tasks=tasks)
    return provider.analyze(items, chronological_items)


def run_event_analysis_llm(
    provider,
    items,
    chronological_items,
    history_context: str | None,
    title: str,
    retry_times: int,
    tasks=None,
):
    """Run, normalize, and validate an LLM event-analysis provider."""
    max_attempts = max(1, retry_times)
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = _analyze_with_provider(provider, items, chronological_items, history_context, tasks=tasks)
            result = normalize_result(result, title=title)
            problems = validate_result(result)
            if problems:
                raise ValueError(f"invalid_llm_result:{','.join(problems)}")
            return result
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                logger.warning("事件大模型分析第 %s/%s 次失败，准备重试: %s", attempt, max_attempts, exc)
    raise last_error or RuntimeError("llm_analysis_failed")

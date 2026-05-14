from datetime import datetime

import pytest

from database import Category, Channel, Info
from services.event_analysis.llm_runner import run_event_analysis_llm
from services.event_analysis.schemas import EventAnalysisResult, TimelinePoint
from services.event_analysis.tasks import default_event_analysis_tasks


def _info(session):
    category = Category(name="科技", code="tech")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()
    item = Info(
        title="Agent 调用链路优化",
        content="Agent 调用链路优化通过规则路由减少无效模型调用，并保留人工可追踪日志。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="llm-runner",
        source_url="https://example.com/llm-runner",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
    )
    session.add(item)
    session.commit()
    return item


def _result(item):
    return EventAnalysisResult(
        one_line_summary="模型生成事件摘要。",
        what_happened="模型说明事件经过。",
        why_it_matters="模型解释事件价值。",
        latest_update="模型总结最新进展。",
        heat_reason="模型判断热度原因。",
        risk_notice="模型提示分析风险。",
        source_compare="模型对比来源差异。",
        analysis_confidence="分析可信度：中。",
        timeline_points=[TimelinePoint(occurred_at=item.event_time, summary="模型生成时间线。", source_item_id=item.id)],
        provider="qwen",
        model_name="qwen-max",
    )


def test_llm_runner_retries_and_validates_provider_result(session):
    item = _info(session)
    attempts = {"count": 0}

    class Provider:
        def analyze(self, items, chronological_items=None):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise TimeoutError("temporary timeout")
            return _result(items[0])

    result = run_event_analysis_llm(Provider(), [item], [item], None, item.title, retry_times=2)

    assert attempts["count"] == 2
    assert result.provider == "qwen"
    assert result.one_line_summary.endswith("。")


def test_llm_runner_rejects_invalid_model_output(session):
    item = _info(session)

    class Provider:
        def analyze(self, items, chronological_items=None, history_context=None):
            result = _result(items[0])
            result.one_line_summary = "短"
            return result

    with pytest.raises(ValueError, match="invalid_llm_result"):
        run_event_analysis_llm(Provider(), [item], [item], "历史背景", item.title, retry_times=1)


def test_llm_runner_rejects_fragmented_model_summary(session):
    item = _info(session)

    class Provider:
        def analyze(self, items, chronological_items=None, history_context=None):
            result = _result(items[0])
            result.one_line_summary = "Agent 调用链路优化正在"
            return result

    with pytest.raises(ValueError, match="one_line_summary_fragment"):
        run_event_analysis_llm(Provider(), [item], [item], "历史背景", item.title, retry_times=1)


def test_llm_runner_passes_task_contract_to_capable_provider(session):
    item = _info(session)
    captured = {}

    class Provider:
        def analyze(self, items, chronological_items=None, history_context=None, tasks=None):
            captured["history_context"] = history_context
            captured["task_codes"] = [task.code for task in tasks]
            return _result(items[0])

    tasks = default_event_analysis_tasks()

    result = run_event_analysis_llm(Provider(), [item], [item], "历史背景", item.title, retry_times=1, tasks=tasks)

    assert result.provider == "qwen"
    assert captured["history_context"] == "历史背景"
    assert captured["task_codes"] == ["summary", "fact_check", "source_compare", "history_relation"]

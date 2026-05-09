from datetime import datetime

from database import Category, Channel, LLMCallLog, LLMModelConfig, Info
from services.event_analysis import analyze_event_sources
from services.analysis.llm_model_config import select_available_llm_config


def _seed_info_and_config(session):
    category = Category(name="AI", code="ai")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()
    info = Info(
        title="Agent 意图识别方案",
        content="Agent 意图识别方案补齐了完整正文，解释了规则路由和模型调用成本。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="llm-log",
        source_url="https://example.com/llm-log",
        event_time=datetime(2026, 5, 8, 12, 0, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=50,
    )
    config = LLMModelConfig(
        provider_name="千问",
        provider_code="qwen",
        base_url="http://127.0.0.1:8001/v1",
        api_key="sk-qwen",
        model_name="qwen-local",
        is_enabled=1,
        daily_call_limit=10,
        daily_call_count=0,
        priority=10,
    )
    session.add_all([info, config])
    session.commit()
    return info, config


def test_event_analysis_records_successful_llm_call_log(session, monkeypatch):
    info, config = _seed_info_and_config(session)

    class FakeProvider:
        def analyze(self, items, chronological_items=None):
            from services.event_analysis.schemas import EventAnalysisResult, TimelinePoint

            return EventAnalysisResult(
                one_line_summary="模型生成的一句话摘要。",
                what_happened="模型生成了事件经过。",
                why_it_matters="模型说明了重要性。",
                latest_update="模型生成最新进展。",
                heat_reason="模型生成热度原因。",
                risk_notice="模型生成风险提示。",
                source_compare="模型生成来源对比。",
                analysis_confidence="分析可信度：高。",
                timeline_points=[TimelinePoint(occurred_at=items[0].event_time, summary="模型生成时间线。", source_item_id=items[0].id)],
                provider="qwen",
                model_name="qwen-local",
                mode="llm",
                quality_score=88,
                confidence=0.82,
            )

    monkeypatch.setattr("services.event_analysis.pipeline.build_llm_provider_from_config", lambda selected: FakeProvider())

    result = analyze_event_sources([info], session=session)

    assert result.provider == "qwen"
    log = session.query(LLMCallLog).one()
    assert log.config_id == config.id
    assert log.provider_code == "qwen"
    assert log.model_name == "qwen-local"
    assert log.status == "succeeded"
    assert log.input_item_count == 1
    assert log.latency_ms >= 0
    assert log.error_message == ""


def test_event_analysis_records_failed_llm_call_log_and_falls_back(session, monkeypatch):
    info, config = _seed_info_and_config(session)

    class FailingProvider:
        def analyze(self, items, chronological_items=None):
            raise RuntimeError("qwen timeout")

    monkeypatch.setattr("services.event_analysis.pipeline.build_llm_provider_from_config", lambda selected: FailingProvider())

    result = analyze_event_sources([info], session=session)

    assert result.provider == "rule"
    assert result.fallback_used is True
    log = session.query(LLMCallLog).one()
    assert log.config_id == config.id
    assert log.status == "failed"
    assert log.error_message == "qwen timeout"


def test_event_analysis_opens_llm_circuit_after_repeated_failures(session, monkeypatch):
    info, config = _seed_info_and_config(session)

    class FailingProvider:
        def analyze(self, items, chronological_items=None):
            raise RuntimeError("qwen timeout")

    monkeypatch.setattr("services.event_analysis.pipeline.build_llm_provider_from_config", lambda selected: FailingProvider())
    monkeypatch.setattr("services.analysis.llm_model_config.EVENT_ANALYSIS_LLM_FAILURE_THRESHOLD", 2)

    analyze_event_sources([info], session=session)
    analyze_event_sources([info], session=session)
    session.refresh(config)

    assert config.consecutive_failure_count == 2
    assert config.circuit_open_until is not None
    assert select_available_llm_config(session) is None

    result = analyze_event_sources([info], session=session)

    assert result.provider == "rule"
    assert result.fallback_used is False
    assert session.query(LLMCallLog).count() == 2

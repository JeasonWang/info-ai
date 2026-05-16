from datetime import datetime

from database import Category, Channel, LLMModelConfig, Info
from services.event_analysis import analyze_event_sources


def test_event_analysis_uses_enabled_model_config_and_counts_call(session, monkeypatch):
    category = Category(name="AI", code="ai")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()
    info = Info(
        title="Agent 意图识别方案",
        content="Agent 意图识别方案补齐了完整正文，解释了规则路由和模型调用成本。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="llm-selection",
        source_url="https://example.com/llm-selection",
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
                timeline_points=[
                    TimelinePoint(
                        occurred_at=items[0].event_time,
                        summary="模型生成时间线。",
                        source_item_id=items[0].id,
                        confidence=0.8,
                    )
                ],
                provider="qwen",
                model_name="qwen-local",
                mode="llm",
                quality_score=88,
                confidence=0.82,
            )

    monkeypatch.setattr("services.event_analysis.pipeline.build_llm_provider_from_config", lambda selected: FakeProvider())

    result = analyze_event_sources([info], session=session)

    assert result.provider == "qwen"
    assert result.model_name == "qwen-local"
    session.refresh(config)
    assert config.daily_call_count == 1


def test_event_analysis_falls_back_to_rule_when_no_model_enabled(session):
    category = Category(name="AI", code="ai")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()
    info = Info(
        title="Agent 意图识别方案",
        content="Agent 意图识别方案补齐了完整正文，解释了规则路由和模型调用成本。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="llm-disabled",
        source_url="https://example.com/llm-disabled",
        event_time=datetime(2026, 5, 8, 12, 0, 0),
    )
    session.add(
        LLMModelConfig(
            provider_name="千问",
            provider_code="qwen",
            base_url="http://127.0.0.1:8001/v1",
            api_key="",
            model_name="qwen-local",
            is_enabled=0,
        )
    )
    session.commit()

    result = analyze_event_sources([info], session=session)

    assert result.provider == "rule"

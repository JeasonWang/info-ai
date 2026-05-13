from datetime import datetime

from database import Category, Channel, Event, EventAnalysisRun, EventItemLink, Info
from services.analysis.event_analysis_quality_report import build_event_analysis_quality_report


def test_event_analysis_quality_report_surfaces_low_confidence_and_weak_sources(session):
    category = Category(name="AI大模型", code="ai")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()

    info = Info(
        title="Agent 意图识别方案",
        content="短内容",
        category_id=category.id,
        channel_id=channel.id,
        source_id="weak-agent",
        source_url="https://example.com/weak-agent",
        event_time=datetime(2026, 5, 8, 10, 0, 0),
        detail_fetch_status="list_only",
        detail_score=20,
        detail_content_length=12,
    )
    event = Event(
        title="Agent 意图识别方案",
        one_line_summary="Agent 意图识别方案正在形成热点讨论。",
        primary_category_id=category.id,
        status="active",
        source_count=1,
        last_updated_at=datetime(2026, 5, 8, 10, 0, 0),
    )
    session.add_all([info, event])
    session.flush()
    session.add(EventItemLink(event_id=event.id, item_id=info.id, role="primary", is_primary=1, weight=20))
    session.add(
        EventAnalysisRun(
            event_id=event.id,
            analysis_version="v1",
            mode="hybrid",
            provider="rule",
            status="fallback",
            input_item_count=1,
            quality_score=42,
            confidence=0.38,
            fallback_used=1,
            failure_reason="local qwen timeout",
            started_at=datetime(2026, 5, 8, 10, 1, 0),
            finished_at=datetime(2026, 5, 8, 10, 1, 2),
        )
    )
    session.commit()

    report = build_event_analysis_quality_report(session, limit=10)

    assert report["summary"]["active_event_count"] == 1
    assert report["summary"]["low_confidence_count"] == 1
    assert report["summary"]["fallback_count"] == 1
    assert report["summary"]["weak_source_event_count"] == 1
    risk_event = report["risk_events"][0]
    assert risk_event["event_id"] == event.id
    assert "low_confidence" in risk_event["issue_reasons"]
    assert "weak_sources" in risk_event["issue_reasons"]
    assert any("详情补偿" in item for item in risk_event["governance_advice"])


def test_event_analysis_quality_report_surfaces_missing_analysis(session):
    category = Category(name="热点事件", code="hot")
    session.add(category)
    session.flush()
    session.add(
        Event(
            title="未分析事件",
            one_line_summary="",
            primary_category_id=category.id,
            status="active",
            source_count=0,
        )
    )
    session.commit()

    report = build_event_analysis_quality_report(session, limit=10)

    assert report["summary"]["missing_analysis_count"] == 1
    assert report["risk_events"][0]["issue_reasons"] == ["missing_analysis"]


def test_event_analysis_quality_report_surfaces_display_quality_blocks(session):
    category = Category(name="热点事件", code="hot")
    session.add(category)
    session.flush()
    session.add_all(
        [
            Event(
                title="可展示事件",
                one_line_summary="可展示事件已有完整事实来源。",
                primary_category_id=category.id,
                status="active",
                source_count=2,
                display_quality_score=82,
                display_quality_level="good",
                display_quality_reason="",
                last_updated_at=datetime(2026, 5, 13, 12, 0, 0),
            ),
            Event(
                title="弱热点线索",
                one_line_summary="弱热点线索仍缺少完整事实来源。",
                primary_category_id=category.id,
                status="monitoring",
                source_count=1,
                display_quality_score=22,
                display_quality_level="weak",
                display_quality_reason="single_weak_source,low_value_content",
                last_updated_at=datetime(2026, 5, 13, 11, 0, 0),
            ),
        ]
    )
    session.commit()

    report = build_event_analysis_quality_report(session, limit=10)
    display_quality = report["display_quality"]

    assert display_quality["summary"]["tracked_event_count"] == 2
    assert display_quality["summary"]["display_ready_count"] == 1
    assert display_quality["summary"]["blocked_count"] == 1
    assert display_quality["summary"]["status_counts"]["monitoring"] == 1
    assert display_quality["summary"]["top_block_reasons"][0] == {"reason": "single_weak_source", "count": 1}
    assert display_quality["blocked_samples"][0]["title"] == "弱热点线索"
    assert "low_value_content" in display_quality["blocked_samples"][0]["display_quality_reasons"]

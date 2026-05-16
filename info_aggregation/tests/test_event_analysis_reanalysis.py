from datetime import datetime

from database import Category, Channel, DetailJob, Event, EventAnalysisRun, EventItemLink, Info
from services.collection.detail_job_worker import process_pending_detail_jobs
from services.collection.detail_pipeline import DetailPipelineResult
from services.analysis.event_analysis_reanalysis import mark_low_confidence_complete_events_stale


def test_detail_job_success_marks_linked_event_analysis_stale(session):
    category = Category(name="AI大模型", code="ai")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()
    info = Info(
        title="Agent 意图识别",
        content="短",
        category_id=category.id,
        channel_id=channel.id,
        source_id="agent-stale",
        source_url="https://example.com/agent-stale",
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=2,
    )
    event = Event(
        title="Agent 意图识别",
        one_line_summary="Agent 意图识别正在形成热点讨论。",
        primary_category_id=category.id,
        status="active",
        source_count=1,
        last_updated_at=datetime(2026, 5, 8, 12, 0, 0),
    )
    session.add_all([info, event])
    session.flush()
    run = EventAnalysisRun(
        event_id=event.id,
        analysis_version="v1",
        mode="rule",
        provider="rule",
        status="succeeded",
        input_item_count=1,
        quality_score=45,
        confidence=0.4,
        started_at=datetime(2026, 5, 8, 12, 1, 0),
        finished_at=datetime(2026, 5, 8, 12, 1, 1),
    )
    session.add_all(
        [
            EventItemLink(event_id=event.id, item_id=info.id, role="primary", is_primary=1, weight=20),
            DetailJob(info_id=info.id, channel_code="juejin", status="pending", priority=90),
            run,
        ]
    )
    session.commit()

    def runner(_info):
        return DetailPipelineResult(
            content="Agent 意图识别方案补齐了完整正文，详细解释了规则路由、模型调用成本和复杂请求处理流程。",
            status="complete",
            strategy="html_article",
            score=92,
            content_length=42,
            failure_reason="",
            matched_rules=[],
        )

    result = process_pending_detail_jobs(session, runner=runner, limit=5)

    assert result == {"succeeded_count": 1, "failed_count": 0}
    session.refresh(run)
    assert run.status == "stale"
    assert run.failure_reason == "detail_compensation_succeeded"


def test_mark_low_confidence_complete_events_stale_only_targets_reanalyzable_events(session):
    category = Category(name="AI大模型", code="ai")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()

    complete_content = (
        "OpenClaw 发布新的 Agent 编排方案，重点改进工具调用、上下文压缩、失败重试和任务规划能力。"
        "文章进一步说明了模型调用成本、权限隔离、执行审计和灰度发布策略，适合企业团队评估工程落地。"
    ) * 8
    complete_info = Info(
        title="OpenClaw Agent 编排方案发布",
        content=complete_content,
        category_id=category.id,
        channel_id=channel.id,
        source_id="complete-reanalyzable",
        source_url="https://example.com/complete-reanalyzable",
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=len(complete_content),
        tech_entities="OpenClaw,Agent",
        tech_keywords="工具调用,上下文压缩",
    )
    weak_info = Info(
        title="弱来源事件",
        content="短",
        category_id=category.id,
        channel_id=channel.id,
        source_id="weak-not-reanalyzable",
        source_url="https://example.com/weak-not-reanalyzable",
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=2,
    )
    complete_event = Event(title="OpenClaw Agent 编排方案发布", one_line_summary="旧摘要", primary_category_id=category.id, status="active", source_count=1)
    weak_event = Event(title="弱来源事件", one_line_summary="旧摘要", primary_category_id=category.id, status="active", source_count=1)
    session.add_all([complete_info, weak_info, complete_event, weak_event])
    session.flush()
    complete_run = EventAnalysisRun(
        event_id=complete_event.id,
        analysis_version="v1",
        mode="rule",
        provider="rule",
        status="succeeded",
        input_item_count=1,
        quality_score=40,
        confidence=0.45,
        started_at=datetime(2026, 5, 15, 8, 0, 0),
        finished_at=datetime(2026, 5, 15, 8, 0, 1),
    )
    weak_run = EventAnalysisRun(
        event_id=weak_event.id,
        analysis_version="v1",
        mode="rule",
        provider="rule",
        status="succeeded",
        input_item_count=1,
        quality_score=40,
        confidence=0.45,
        started_at=datetime(2026, 5, 15, 8, 0, 0),
        finished_at=datetime(2026, 5, 15, 8, 0, 1),
    )
    session.add_all(
        [
            EventItemLink(event_id=complete_event.id, item_id=complete_info.id, role="primary", is_primary=1, weight=90),
            EventItemLink(event_id=weak_event.id, item_id=weak_info.id, role="primary", is_primary=1, weight=20),
            complete_run,
            weak_run,
        ]
    )
    session.commit()

    result = mark_low_confidence_complete_events_stale(session, limit=10)

    assert result["marked_count"] == 1
    assert result["candidate_count"] == 1
    session.refresh(complete_run)
    session.refresh(weak_run)
    assert complete_run.status == "stale"
    assert complete_run.failure_reason == "low_confidence_complete_source_reanalysis"
    assert weak_run.status == "succeeded"


def test_mark_low_confidence_complete_events_stale_allows_single_weak_two_source_events(session):
    category = Category(name="国际", code="international")
    reuters = Channel(name="路透社", code="reuters", category_rel=category)
    session.add_all([category, reuters])
    session.flush()

    strong_content = (
        "Reuters reported that markets are watching policy signals, inflation trends and government comments closely."
        " The article explains how investors are balancing near-term volatility with longer-term expectations for rates, trade and growth."
    ) * 5
    strong_info = Info(
        title="Reuters markets briefing",
        content=strong_content,
        category_id=category.id,
        channel_id=reuters.id,
        source_id="strong-reuters",
        source_url="https://example.com/strong-reuters",
        detail_fetch_status="complete",
        detail_score=95,
        detail_content_length=len(strong_content),
    )
    weak_info = Info(
        title="Reuters markets briefing",
        content="短",
        category_id=category.id,
        channel_id=reuters.id,
        source_id="weak-reuters",
        source_url="https://example.com/weak-reuters",
        detail_fetch_status="partial",
        detail_score=45,
        detail_content_length=120,
    )
    event = Event(title="Reuters markets briefing", one_line_summary="旧摘要", primary_category_id=category.id, status="active", source_count=2)
    session.add_all([strong_info, weak_info, event])
    session.flush()
    run = EventAnalysisRun(
        event_id=event.id,
        analysis_version="v1",
        mode="rule",
        provider="rule",
        status="succeeded",
        input_item_count=2,
        quality_score=52,
        confidence=0.55,
        started_at=datetime(2026, 5, 15, 8, 0, 0),
        finished_at=datetime(2026, 5, 15, 8, 0, 1),
    )
    session.add_all(
        [
            EventItemLink(event_id=event.id, item_id=strong_info.id, role="primary", is_primary=1, weight=90),
            EventItemLink(event_id=event.id, item_id=weak_info.id, role="secondary", is_primary=0, weight=10),
            run,
        ]
    )
    session.commit()

    result = mark_low_confidence_complete_events_stale(session, limit=10)

    assert result["marked_count"] == 1
    session.refresh(run)
    assert run.status == "stale"
    assert run.failure_reason == "low_confidence_complete_source_reanalysis"

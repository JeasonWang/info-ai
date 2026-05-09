from datetime import datetime

from database import Category, Channel, DetailJob, Event, EventAnalysisRun, EventItemLink, Info
from services.collection.detail_job_worker import process_pending_detail_jobs
from services.collection.detail_pipeline import DetailPipelineResult


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

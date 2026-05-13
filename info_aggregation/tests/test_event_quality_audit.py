from datetime import datetime

from database import Category, Channel, Event, EventAnalysisRun, Info, LLMCallLog
from tools.event_quality_audit import build_event_quality_audit


def test_event_quality_audit_counts_channel_event_and_llm_risks(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="微博",
        code="weibo",
        base_url="https://weibo.com",
        category_id=category.id,
        is_active=1,
    )
    session.add(channel)
    session.flush()

    weak_info = Info(
        title="微博热榜话题",
        content="互动：点赞10万+",
        category_id=category.id,
        channel_id=channel.id,
        source_id="audit-weak",
        source_url="https://example.com/audit-weak",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=9,
    )
    good_info = Info(
        title="微博话题后续通报",
        content="相关部门发布通报，说明事件处置进展和后续安排，多个平台开始跟进报道。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="audit-good",
        source_url="https://example.com/audit-good",
        event_time=datetime(2026, 5, 13, 10, 5, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=40,
    )
    session.add_all([weak_info, good_info])
    session.flush()

    bad_event = Event(
        title="微博热榜话题",
        one_line_summary="互动：点赞10万+。",
        primary_category_id=category.id,
        status="active",
        source_count=1,
        last_updated_at=datetime(2026, 5, 13, 10, 0, 0),
    )
    session.add(bad_event)
    session.flush()
    session.add(
        EventAnalysisRun(
            event_id=bad_event.id,
            mode="rule",
            provider="rule",
            status="fallback",
            input_item_count=1,
            fallback_used=1,
            quality_score=20,
            confidence=0.3,
        )
    )
    session.add(
        LLMCallLog(
            config_id=1,
            provider_code="qwen",
            model_name="qwen-test",
            status="failed",
            latency_ms=60000,
            input_item_count=1,
            error_message="The read operation timed out",
        )
    )
    session.commit()

    report = build_event_quality_audit(session)

    assert report["channels"]["weibo"]["total_count"] == 2
    assert report["channels"]["weibo"]["list_only_count"] == 1
    assert report["events"]["active_event_count"] == 1
    assert report["events"]["short_summary_count"] == 0
    assert report["events"]["low_value_summary_count"] == 1
    assert report["events"]["single_source_active_count"] == 1
    assert report["analysis"]["fallback_run_count"] == 1
    assert report["llm"]["failed_call_count"] == 1
    assert report["llm"]["latest_failure_reason"] == "The read operation timed out"

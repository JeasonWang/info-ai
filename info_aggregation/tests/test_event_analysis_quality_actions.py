from datetime import datetime

from database import Category, Channel, DetailJob, Event, EventAnalysisRun, EventItemLink, Info
from services.analysis.event_analysis_quality_actions import enqueue_event_analysis_detail_jobs


def test_enqueue_event_analysis_detail_jobs_targets_weak_sources_from_risk_events(session):
    category = Category(name="AI大模型", code="ai")
    channel = Channel(name="知乎", code="zhihu", category_rel=category)
    session.add_all([category, channel])
    session.flush()

    weak_info = Info(
        title="Agent 意图识别弱来源",
        content="短",
        category_id=category.id,
        channel_id=channel.id,
        source_id="weak-agent",
        source_url="https://example.com/weak-agent",
        event_time=datetime(2026, 5, 8, 11, 0, 0),
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=2,
    )
    good_info = Info(
        title="Agent 意图识别完整来源",
        content="这是一段足够完整的正文，包含多个事实和上下文，可以支撑事件分析使用。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="good-agent",
        source_url="https://example.com/good-agent",
        event_time=datetime(2026, 5, 8, 11, 5, 0),
        detail_fetch_status="complete",
        detail_score=88,
        detail_content_length=80,
    )
    event = Event(
        title="Agent 意图识别方案",
        one_line_summary="Agent 意图识别方案正在形成热点讨论。",
        primary_category_id=category.id,
        status="active",
        source_count=2,
        last_updated_at=datetime(2026, 5, 8, 11, 5, 0),
    )
    session.add_all([weak_info, good_info, event])
    session.flush()
    session.add_all(
        [
            EventItemLink(event_id=event.id, item_id=weak_info.id, role="primary", is_primary=1, weight=20),
            EventItemLink(event_id=event.id, item_id=good_info.id, role="media", is_primary=0, weight=80),
            EventAnalysisRun(
                event_id=event.id,
                analysis_version="v1",
                mode="hybrid",
                provider="rule",
                status="fallback",
                input_item_count=2,
                quality_score=45,
                confidence=0.4,
                fallback_used=1,
                failure_reason="qwen timeout",
                started_at=datetime(2026, 5, 8, 11, 6, 0),
                finished_at=datetime(2026, 5, 8, 11, 6, 1),
            ),
        ]
    )
    session.commit()

    result = enqueue_event_analysis_detail_jobs(session, limit=10)

    assert result["created_count"] == 1
    assert result["skipped_count"] == 0
    assert result["risk_event_count"] == 1
    assert result["selected_samples"][0]["info_id"] == weak_info.id
    job = session.query(DetailJob).one()
    assert job.info_id == weak_info.id
    assert job.channel_code == "zhihu"
    assert job.priority >= 90
    assert job.strategy_hint


def test_enqueue_event_analysis_detail_jobs_skips_existing_open_job(session):
    category = Category(name="热点事件", code="hot")
    channel = Channel(name="微博", code="weibo", category_rel=category)
    session.add_all([category, channel])
    session.flush()
    info = Info(
        title="弱来源",
        content="短",
        category_id=category.id,
        channel_id=channel.id,
        source_id="weak",
        source_url="https://example.com/weak",
        detail_fetch_status="failed",
        detail_score=0,
        detail_content_length=0,
    )
    event = Event(title="弱事件", one_line_summary="", primary_category_id=category.id, status="active", source_count=1)
    session.add_all([info, event])
    session.flush()
    session.add_all(
        [
            EventItemLink(event_id=event.id, item_id=info.id, role="primary", is_primary=1, weight=10),
            DetailJob(info_id=info.id, channel_code="weibo", status="pending", priority=80),
        ]
    )
    session.commit()

    result = enqueue_event_analysis_detail_jobs(session, limit=10)

    assert result["created_count"] == 0
    assert result["skipped_count"] == 1
    assert session.query(DetailJob).count() == 1


def test_enqueue_event_analysis_detail_jobs_targets_high_weak_ratio_successful_events(session):
    category = Category(name="热点事件", code="hot")
    weak_channel = Channel(name="微博", code="weibo", category_rel=category)
    good_channel = Channel(name="今日头条", code="toutiao", category_rel=category)
    session.add_all([category, weak_channel, good_channel])
    session.flush()

    event = Event(
        title="支付宝正寻求警方帮助",
        one_line_summary="支付宝相关争议已有多平台讨论，仍需关注权威进展。",
        primary_category_id=category.id,
        status="active",
        source_count=6,
        last_updated_at=datetime(2026, 5, 15, 9, 0, 0),
    )
    session.add(event)
    session.flush()

    infos = []
    for index in range(5):
        info = Info(
            title=f"支付宝正寻求警方帮助 {index}",
            content="短",
            category_id=category.id,
            channel_id=weak_channel.id,
            source_id=f"weak-alipay-{index}",
            source_url=f"https://example.com/weak-alipay-{index}",
            event_time=datetime(2026, 5, 15, 9, index, 0),
            detail_fetch_status="pending",
            detail_score=10,
            detail_content_length=2,
        )
        infos.append(info)
    good_info = Info(
        title="支付宝正寻求警方帮助 事实源",
        content="支付宝相关争议已有较完整事实源，包含主体、处置进展和后续关注点。" * 6,
        category_id=category.id,
        channel_id=good_channel.id,
        source_id="good-alipay",
        source_url="https://example.com/good-alipay",
        event_time=datetime(2026, 5, 15, 9, 6, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=240,
    )
    session.add_all([*infos, good_info])
    session.flush()
    session.add_all(
        [
            EventItemLink(event_id=event.id, item_id=info.id, role="social", is_primary=0, weight=20)
            for info in infos
        ]
    )
    session.add(EventItemLink(event_id=event.id, item_id=good_info.id, role="media", is_primary=1, weight=90))
    session.add(
        EventAnalysisRun(
            event_id=event.id,
            analysis_version="v1",
            mode="hybrid",
            provider="qwen",
            status="succeeded",
            input_item_count=6,
            quality_score=98,
            confidence=0.72,
            fallback_used=0,
            started_at=datetime(2026, 5, 15, 9, 7, 0),
            finished_at=datetime(2026, 5, 15, 9, 7, 1),
        )
    )
    session.commit()

    result = enqueue_event_analysis_detail_jobs(session, limit=10)

    assert result["risk_event_count"] == 1
    assert result["created_count"] == 5
    assert {sample["event_id"] for sample in result["selected_samples"]} == {event.id}
    assert session.query(DetailJob).count() == 5

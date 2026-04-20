from datetime import datetime

from database import (
    Category,
    Channel,
    Event,
    EventItemLink,
    InfoAcquisitionLog,
    EventSummarySnapshot,
    EventTimelineEntry,
    Info,
)


def test_event_models_can_persist_relationships(session):
    category = Category(name="科技", code="tech", description="科技事件")
    session.add(category)
    session.flush()

    channel = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()

    info = Info(
        title="OpenAI 发布新模型能力",
        content="OpenAI 公布了新一代模型能力更新。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="seed-001",
        source_url="https://example.com/seed-001",
        event_time=datetime(2026, 4, 19, 10, 0, 0),
        core_entity="OpenAI",
    )
    session.add(info)
    session.flush()

    event = Event(
        title="OpenAI 发布新模型能力",
        one_line_summary="多个平台正在讨论 OpenAI 新模型发布。",
        primary_category_id=category.id,
        status="active",
        heat_score=95,
        freshness_score=88,
        composite_score=91,
        source_count=1,
        started_at=info.event_time,
        last_updated_at=info.event_time,
    )
    session.add(event)
    session.flush()

    session.add(
        EventItemLink(
            event_id=event.id,
            item_id=info.id,
            role="primary",
            is_primary=1,
            weight=100,
        )
    )
    session.add(
        EventSummarySnapshot(
            event_id=event.id,
            summary_type="one_line",
            content="多个平台正在讨论 OpenAI 新模型发布。",
            version=1,
        )
    )
    session.add(
        EventTimelineEntry(
            event_id=event.id,
            occurred_at=info.event_time,
            summary="官方渠道首先发布了核心更新。",
            source_item_id=info.id,
            confidence=0.95,
            display_order=1,
        )
    )
    session.commit()

    assert session.query(Event).count() == 1
    assert session.query(EventItemLink).count() == 1
    assert session.query(EventSummarySnapshot).count() == 1
    assert session.query(EventTimelineEntry).count() == 1


def test_info_quality_fields_and_acquisition_logs_can_persist(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()

    channel = Channel(
        name="微博",
        code="weibo",
        base_url="https://weibo.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()

    info = Info(
        title="微博热搜样例",
        content="列表摘要",
        category_id=category.id,
        channel_id=channel.id,
        source_id="wb-1",
        source_url="https://example.com/wb-1",
        detail_fetch_status="partial",
        detail_fetch_error="content_too_short",
        detail_strategy="topic_search",
        detail_score=72,
        detail_content_length=168,
    )
    session.add(info)
    session.flush()

    session.add(
        InfoAcquisitionLog(
            info_id=info.id,
            channel_code="weibo",
            strategy="topic_search",
            status="partial",
            score=72,
            content_length=168,
            failure_reason="content_too_short",
            matched_rules="short_content",
            raw_excerpt="微博正文样例",
        )
    )
    session.commit()

    saved = session.query(Info).first()
    assert saved.detail_fetch_status == "partial"
    assert saved.detail_strategy == "topic_search"
    assert saved.detail_score == 72
    assert session.query(InfoAcquisitionLog).count() == 1

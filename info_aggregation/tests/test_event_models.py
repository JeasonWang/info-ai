from datetime import datetime

from database import (
    Category,
    Channel,
    Event,
    EventItemLink,
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

from datetime import datetime

from fastapi.testclient import TestClient

from api import app
from database import Category, Channel, Event, Info


def test_admin_rebuild_events_refreshes_event_tables(session):
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

    session.add(
        Info(
            title="OpenAI 发布新模型能力",
            content="媒体开始追踪模型能力升级。",
            category_id=category.id,
            channel_id=channel.id,
            source_id="rebuild-001",
            source_url="https://example.com/rebuild-001",
            event_time=datetime(2026, 4, 19, 9, 0, 0),
            core_entity="OpenAI",
        )
    )
    session.commit()

    client = TestClient(app)
    response = client.post("/api/admin/rebuild-events")
    assert response.status_code == 200
    assert response.json()["data"]["event_count"] == 1
    assert session.query(Event).count() == 1

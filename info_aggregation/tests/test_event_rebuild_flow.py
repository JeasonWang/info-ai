from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from api import app
from crawlers.registry import crawler_registry
from database import Category, Channel, Event, Info, InfoAcquisitionLog
from scheduler import _fetch_details_for_items
from services.detail_pipeline import DetailPipelineResult


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


def test_admin_rebuild_events_clears_user_event_dependencies(session):
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
            title="大模型工具发布新版本",
            content="开发者开始关注新版本的大模型编程辅助能力。",
            category_id=category.id,
            channel_id=channel.id,
            source_id="rebuild-user-dependency-001",
            source_url="https://example.com/rebuild-user-dependency-001",
            event_time=datetime(2026, 4, 22, 9, 0, 0),
            core_entity="大模型工具",
        )
    )
    session.commit()

    client = TestClient(app)
    response = client.post("/api/admin/rebuild-events")
    assert response.status_code == 200
    event_id = session.query(Event.id).scalar()

    session.execute(text("CREATE TABLE user_account (id INTEGER PRIMARY KEY, email TEXT)"))
    session.execute(
        text(
            "CREATE TABLE user_favorite_event ("
            "id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, event_id INTEGER)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE user_read_history ("
            "id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, event_id INTEGER, info_id INTEGER)"
        )
    )
    session.execute(text("INSERT INTO user_account (id, email) VALUES (1, 'reader@example.com')"))
    session.execute(
        text("INSERT INTO user_favorite_event (user_id, event_id) VALUES (1, :event_id)"),
        {"event_id": event_id},
    )
    session.execute(
        text("INSERT INTO user_read_history (user_id, event_id) VALUES (1, :event_id)"),
        {"event_id": event_id},
    )
    session.commit()

    response = client.post("/api/admin/rebuild-events")

    assert response.status_code == 200
    assert session.execute(text("SELECT COUNT(*) FROM user_favorite_event")).scalar() == 0
    assert session.execute(text("SELECT COUNT(*) FROM user_read_history")).scalar() == 0


def test_admin_refresh_quality_recomputes_semantics_and_rebuilds_events(session):
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
            title="英伟达发布H200芯片",
            content="H200 芯片面向大模型训练场景，开发者开始讨论显存和训练效率。",
            category_id=category.id,
            channel_id=channel.id,
            source_id="refresh-quality-001",
            source_url="https://example.com/refresh-quality-001",
            event_time=datetime(2026, 4, 21, 9, 0, 0),
        )
    )
    session.commit()

    client = TestClient(app)
    response = client.post("/api/admin/refresh-quality")
    assert response.status_code == 200

    payload = response.json()["data"]
    refreshed = session.query(Info).filter(Info.source_id == "refresh-quality-001").first()
    assert payload["processed_count"] == 1
    assert payload["changed_count"] == 1
    assert payload["event_count"] == 1
    assert refreshed.tech_topic_type == "chip_release"
    assert "显存" in refreshed.tech_keywords


def test_fetch_details_for_items_persists_quality_metadata(session, monkeypatch):
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
        title="OpenAI 发布新模型",
        content="列表摘要",
        category_id=category.id,
        channel_id=channel.id,
        source_id="detail-001",
        source_url="https://example.com/detail-001",
        event_time=datetime(2026, 4, 20, 9, 0, 0),
        core_entity="OpenAI",
    )
    session.add(info)
    session.commit()
    info_id = info.id

    class DummyCrawler:
        def safe_fetch_detail(self, source_url, item):
            pipeline = DetailPipelineResult(
                content="OpenAI 发布会上介绍了新模型、价格和接入计划，讨论持续升温。",
                status="complete",
                strategy="topic_search",
                score=88,
                content_length=35,
                failure_reason="",
                matched_rules=[],
            )
            return pipeline.content, pipeline.status, pipeline.failure_reason, pipeline

    crawler_registry.register("weibo", DummyCrawler())
    monkeypatch.setattr("scheduler.time.sleep", lambda _: None)
    monkeypatch.setattr("scheduler.random.uniform", lambda a, b: 0)

    _fetch_details_for_items("weibo", [info_id])

    refreshed = session.query(Info).filter(Info.id == info_id).first()
    assert refreshed.detail_fetch_status == "complete"
    assert refreshed.detail_strategy == "topic_search"
    assert refreshed.detail_score >= 80
    assert refreshed.tech_topic_type == "model_release"
    assert "OpenAI" in refreshed.tech_entities
    assert session.query(InfoAcquisitionLog).count() == 1

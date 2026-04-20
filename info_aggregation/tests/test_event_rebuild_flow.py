from datetime import datetime

from fastapi.testclient import TestClient

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
    assert session.query(InfoAcquisitionLog).count() == 1

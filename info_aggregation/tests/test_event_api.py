from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from api import app
from database import Category, Channel, Info
from services.event_builder import rebuild_events


def seed_event_data(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    international = Category(name="国际", code="international", description="国际事件")
    session.add_all([tech, international])
    session.flush()

    kr = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    reu = Channel(
        name="路透社",
        code="reuters",
        base_url="https://reuters.com",
        category_id=international.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add_all([kr, reu])
    session.flush()

    now = datetime(2026, 4, 19, 12, 0, 0)
    session.add_all(
        [
            Info(
                title="OpenAI 发布新模型能力",
                content="媒体正在讨论 OpenAI 模型能力升级。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="tech-1",
                source_url="https://example.com/tech-1",
                event_time=now,
                core_entity="OpenAI",
            ),
            Info(
                title="OpenAI 新模型价格方案曝光",
                content="多个平台开始关注定价和开放范围。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="tech-2",
                source_url="https://example.com/tech-2",
                event_time=now + timedelta(minutes=20),
                core_entity="OpenAI",
            ),
            Info(
                title="联合国气候峰会达成新协议",
                content="国际媒体关注减排目标变化。",
                category_id=international.id,
                channel_id=reu.id,
                source_id="int-1",
                source_url="https://example.com/int-1",
                event_time=now - timedelta(hours=2),
                core_entity="联合国",
            ),
        ]
    )
    session.commit()


def test_list_events_returns_grouped_cards(session):
    seed_event_data(session)
    rebuild_events(session)
    client = TestClient(app)

    response = client.get("/api/events?category_code=tech&page=1&page_size=10")
    assert response.status_code == 200

    payload = response.json()["data"]
    assert payload["items"][0]["title"] == "OpenAI 发布新模型能力"
    assert payload["items"][0]["source_count"] == 2
    assert "OpenAI" in payload["items"][0]["one_line_summary"]
    assert payload["items"][0]["representative_info_id"]


def test_get_event_returns_timeline_and_summaries(session):
    seed_event_data(session)
    rebuild_events(session)
    client = TestClient(app)

    list_response = client.get("/api/events?category_code=all&page=1&page_size=10")
    event_id = list_response.json()["data"]["items"][0]["id"]

    detail_response = client.get(f"/api/events/{event_id}")
    assert detail_response.status_code == 200

    payload = detail_response.json()["data"]
    assert payload["event"]["id"] == event_id
    assert len(payload["timeline"]) >= 1
    assert payload["summaries"]["why_it_matters"]
    assert len(payload["representative_sources"]) >= 1
    assert payload["summaries"]["what_happened"] != payload["summaries"]["latest_update"]


def test_list_events_supports_keyword_filtering(session):
    seed_event_data(session)
    rebuild_events(session)
    client = TestClient(app)

    response = client.get("/api/events?category_code=all&keyword=OpenAI&page=1&page_size=10")
    assert response.status_code == 200

    payload = response.json()["data"]
    assert len(payload["items"]) == 1
    assert "OpenAI" in payload["items"][0]["title"]


def test_list_infos_returns_acquisition_quality_fields(session):
    seed_event_data(session)
    info = session.query(Info).filter(Info.source_id == "tech-1").first()
    info.detail_fetch_status = "complete"
    info.detail_fetch_error = ""
    info.detail_strategy = "topic_search"
    info.detail_score = 86
    info.detail_content_length = 188
    info.detail_fetched_at = datetime(2026, 4, 20, 8, 30, 0)
    session.commit()

    client = TestClient(app)
    response = client.get("/api/infos?page=1&page_size=10")
    assert response.status_code == 200

    payload = response.json()["data"]
    target = next(item for item in payload["items"] if item["source_id"] == "tech-1")
    assert target["detail_fetch_status"] == "complete"
    assert target["detail_strategy"] == "topic_search"
    assert target["detail_score"] == 86
    assert target["detail_content_length"] == 188
    assert target["detail_fetched_at"] == "2026-04-20 08:30:00"

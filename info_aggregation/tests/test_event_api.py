from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from api import app
from database import Category, Channel, Event, Info
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
    assert "已出现多来源跟进" in payload["items"][0]["one_line_summary"]


def test_event_one_line_summary_is_natural_for_single_source(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()

    kr = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(kr)
    session.flush()

    session.add(
        Info(
            title="Anthropic 发布新模型",
            content="媒体开始追踪新模型能力。",
            category_id=tech.id,
            channel_id=kr.id,
            source_id="single-1",
            source_url="https://example.com/single-1",
            event_time=datetime(2026, 4, 20, 9, 0, 0),
            core_entity="Anthropic",
            tech_topic_type="model_release",
        )
    )
    session.commit()
    rebuild_events(session)

    client = TestClient(app)
    response = client.get("/api/events?category_code=tech&page=1&page_size=10")
    assert response.status_code == 200

    summary = response.json()["data"]["items"][0]["one_line_summary"]
    assert "媒体开始追踪新模型能力" in summary
    assert "已聚合" not in summary


def test_event_one_line_summary_avoids_repeating_title_for_single_source(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()

    kr = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(kr)
    session.flush()

    session.add(
        Info(
            title="OpenAI 发布新模型",
            content="OpenAI 发布新模型后，开发者重点关注 API 接入节奏、推理性能和部署成本。",
            category_id=tech.id,
            channel_id=kr.id,
            source_id="single-repeat-1",
            source_url="https://example.com/single-repeat-1",
            event_time=datetime(2026, 4, 20, 9, 0, 0),
            core_entity="OpenAI",
            tech_topic_type="model_release",
        )
    )
    session.commit()
    rebuild_events(session)

    client = TestClient(app)
    response = client.get("/api/events?category_code=tech&page=1&page_size=10")
    assert response.status_code == 200

    item = response.json()["data"]["items"][0]
    assert item["title"] == "OpenAI 发布新模型"
    assert item["one_line_summary"] != item["title"]
    assert "API 接入节奏" in item["one_line_summary"]


def test_rebuild_events_prefers_high_quality_source_as_event_lead(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()

    kr = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(kr)
    session.flush()

    session.add_all(
        [
            Info(
                title="OpenAI 发布新模型",
                content="OpenAI 发布新模型",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="quality-low",
                source_url="https://example.com/quality-low",
                event_time=datetime(2026, 4, 20, 9, 0, 0),
                core_entity="OpenAI",
                detail_fetch_status="list_only",
                detail_score=10,
                detail_content_length=12,
            ),
            Info(
                title="OpenAI 新模型开发者反馈",
                content="OpenAI 新模型发布后，开发者重点关注 API 接入节奏、推理性能和部署成本，企业团队开始评估迁移方案。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="quality-high",
                source_url="https://example.com/quality-high",
                event_time=datetime(2026, 4, 20, 9, 5, 0),
                core_entity="OpenAI",
                detail_fetch_status="complete",
                detail_score=90,
                detail_content_length=86,
            ),
        ]
    )
    session.commit()
    rebuild_events(session)

    client = TestClient(app)
    response = client.get("/api/events?category_code=tech&page=1&page_size=10")
    assert response.status_code == 200

    item = response.json()["data"]["items"][0]
    assert item["title"] == "OpenAI 新模型开发者反馈"
    assert "API 接入节奏" in item["one_line_summary"]


def test_list_events_deduplicates_source_badges(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()

    kr = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(kr)
    session.flush()

    session.add_all(
        [
            Info(
                title="OpenAI 发布新模型",
                content="OpenAI 发布新模型后，开发者重点关注 API 接入节奏。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="badge-1",
                source_url="https://example.com/badge-1",
                event_time=datetime(2026, 4, 20, 9, 0, 0),
                core_entity="OpenAI",
                detail_fetch_status="complete",
            ),
            Info(
                title="OpenAI 新模型价格方案",
                content="OpenAI 新模型价格方案继续引发开发者讨论。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="badge-2",
                source_url="https://example.com/badge-2",
                event_time=datetime(2026, 4, 20, 9, 5, 0),
                core_entity="OpenAI",
                detail_fetch_status="complete",
            ),
        ]
    )
    session.commit()
    rebuild_events(session)

    client = TestClient(app)
    response = client.get("/api/events?category_code=tech&page=1&page_size=10")
    assert response.status_code == 200

    badges = response.json()["data"]["items"][0]["source_badges"]
    assert badges == ["36氪"]


def test_get_event_detail_deduplicates_timeline_and_source_views(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()

    kr = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(kr)
    session.flush()

    session.add_all(
        [
            Info(
                title="OpenAI 发布新模型",
                content="OpenAI 发布新模型后，开发者重点关注 API 接入节奏和部署成本。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="detail-dedupe-1",
                source_url="https://example.com/detail-dedupe-1",
                event_time=datetime(2026, 4, 20, 9, 0, 0),
                core_entity="OpenAI",
                detail_fetch_status="complete",
            ),
            Info(
                title="OpenAI 发布新模型后续",
                content="OpenAI 发布新模型后，开发者重点关注 API 接入节奏和部署成本。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id="detail-dedupe-2",
                source_url="https://example.com/detail-dedupe-2",
                event_time=datetime(2026, 4, 20, 9, 5, 0),
                core_entity="OpenAI",
                detail_fetch_status="complete",
            ),
        ]
    )
    session.commit()
    rebuild_events(session)

    client = TestClient(app)
    list_response = client.get("/api/events?category_code=tech&page=1&page_size=10")
    event_id = list_response.json()["data"]["items"][0]["id"]
    detail_response = client.get(f"/api/events/{event_id}")
    assert detail_response.status_code == 200

    payload = detail_response.json()["data"]
    assert payload["timeline"] == []
    assert payload["source_views"] == []


def test_event_one_line_summary_mentions_aggregated_count_for_many_sources(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()

    kr = Channel(
        name="36氪",
        code="36kr",
        base_url="https://36kr.com",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(kr)
    session.flush()

    for index in range(4):
        session.add(
            Info(
                title=f"英伟达 H200 讨论 {index}",
                content="多平台正在跟进芯片能力和训练效率。",
                category_id=tech.id,
                channel_id=kr.id,
                source_id=f"multi-{index}",
                source_url=f"https://example.com/multi-{index}",
                event_time=datetime(2026, 4, 20, 9, index, 0),
                core_entity="英伟达",
                tech_topic_type="chip_release",
            )
        )
    session.commit()
    rebuild_events(session)

    client = TestClient(app)
    response = client.get("/api/events?category_code=tech&page=1&page_size=10")
    assert response.status_code == 200

    summary = response.json()["data"]["items"][0]["one_line_summary"]
    assert "英伟达" in summary
    assert "持续升温" in summary
    assert "已聚合 4 条来源内容" in summary


def test_get_event_returns_timeline_and_summaries(session):
    seed_event_data(session)
    lead = session.query(Info).filter(Info.source_id == "tech-1").first()
    follow = session.query(Info).filter(Info.source_id == "tech-2").first()
    lead.tech_topic_type = "model_release"
    lead.tech_entities = "OpenAI,GPT-5"
    lead.tech_keywords = "推理,API"
    follow.tech_topic_type = "dev_tool"
    follow.tech_entities = "OpenAI,MCP"
    follow.tech_keywords = "API,开发工具"
    lead.content = "OpenAI 发布新模型能力后，多个平台开始追踪推理性能、API 开放范围和开发者接入节奏。"
    follow.content = "多个平台开始关注定价和开放范围。"
    session.commit()
    rebuild_events(session)
    client = TestClient(app)

    list_response = client.get("/api/events?category_code=all&page=1&page_size=10")
    event_id = list_response.json()["data"]["items"][0]["id"]

    detail_response = client.get(f"/api/events/{event_id}")
    assert detail_response.status_code == 200

    payload = detail_response.json()["data"]
    assert payload["event"]["id"] == event_id
    assert "timeline" in payload
    assert payload["summaries"]["why_it_matters"]
    assert len(payload["representative_sources"]) >= 1
    assert payload["summaries"]["what_happened"] != payload["summaries"]["latest_update"]
    assert "推理" in payload["summaries"]["what_happened"] or "API" in payload["summaries"]["what_happened"]
    assert "OpenAI" in payload["summaries"]["why_it_matters"]
    assert "API" in payload["summaries"]["latest_update"] or "开发工具" in payload["summaries"]["latest_update"]
    assert payload["tech_context"]["topics"][0]["topic_type"] == "dev_tool" or payload["tech_context"]["topics"][0]["topic_type"] == "model_release"
    assert "OpenAI" in payload["tech_context"]["entities"]
    assert "API" in payload["tech_context"]["keywords"]


def test_list_events_supports_keyword_filtering(session):
    seed_event_data(session)
    rebuild_events(session)
    client = TestClient(app)

    response = client.get("/api/events?category_code=all&keyword=OpenAI&page=1&page_size=10")
    assert response.status_code == 200

    payload = response.json()["data"]
    assert len(payload["items"]) == 1
    assert "OpenAI" in payload["items"][0]["title"]


def test_list_events_supports_latest_sort(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()
    session.add_all(
        [
            Event(
                title="高综合分较早事件",
                one_line_summary="综合分更高但更新时间更早。",
                primary_category_id=tech.id,
                composite_score=98,
                heat_score=98,
                last_updated_at=datetime(2026, 4, 19, 9, 0, 0),
            ),
            Event(
                title="最新更新事件",
                one_line_summary="综合分较低但更新时间最新。",
                primary_category_id=tech.id,
                composite_score=80,
                heat_score=80,
                last_updated_at=datetime(2026, 4, 20, 9, 0, 0),
            ),
        ]
    )
    session.commit()

    client = TestClient(app)
    response = client.get("/api/events?category_code=all&sort=latest&page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["title"] == "最新更新事件"


def test_list_infos_returns_acquisition_quality_fields(session):
    seed_event_data(session)
    info = session.query(Info).filter(Info.source_id == "tech-1").first()
    info.detail_fetch_status = "complete"
    info.detail_fetch_error = ""
    info.detail_strategy = "topic_search"
    info.detail_score = 86
    info.detail_content_length = 188
    info.detail_fetched_at = datetime(2026, 4, 20, 8, 30, 0)
    info.tech_topic_type = "model_release"
    info.tech_entities = "OpenAI"
    info.tech_keywords = "推理,API"
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
    assert target["tech_topic_type"] == "model_release"
    assert target["tech_keywords"] == ["推理", "API"]


def test_get_info_returns_tech_semantic_fields(session):
    seed_event_data(session)
    info = session.query(Info).filter(Info.source_id == "tech-2").first()
    info.tech_topic_type = "dev_tool"
    info.tech_entities = "OpenAI,MCP"
    info.tech_keywords = "API,开发工具"
    session.commit()

    client = TestClient(app)
    response = client.get(f"/api/infos/{info.id}")
    assert response.status_code == 200

    payload = response.json()["data"]
    assert payload["tech_topic_type"] == "dev_tool"
    assert payload["tech_entities"] == ["OpenAI", "MCP"]
    assert payload["tech_keywords"] == ["API", "开发工具"]

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from api import app
import api
from crawlers.registry import crawler_registry
from database import Category, Channel, Event, EventItemLink, Info
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


def test_trigger_crawl_returns_accepted_without_waiting_for_crawler(monkeypatch):
    class SlowCrawler:
        channel_code = "zhihu"

        def safe_crawl(self):
            raise AssertionError("endpoint should schedule background task instead of crawling inline")

    triggered = []
    previous = crawler_registry.get("zhihu")
    crawler_registry.register("zhihu", SlowCrawler())
    monkeypatch.setattr(api, "_run_manual_crawl", lambda channel_code: triggered.append(channel_code))
    try:
        client = TestClient(app)
        response = client.post("/api/crawl/trigger?channel_code=zhihu")
    finally:
        if previous:
            crawler_registry.register("zhihu", previous)

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "采集任务已提交，后台执行中"
    assert payload["data"] == {
        "channel": "zhihu",
        "status": "accepted",
        "trigger_type": "manual",
    }
    assert triggered == ["zhihu"]


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


def test_rebuild_events_orders_event_links_by_quality_not_time(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()
    channel = Channel(name="36氪", code="36kr", base_url="https://36kr.com", category_id=tech.id)
    session.add(channel)
    session.flush()
    older_quality = Info(
        title="OpenAI 新模型完整分析",
        content=(
            "OpenAI 新模型发布后，开发者关注 API 接入节奏、推理性能、上下文窗口、部署成本和企业迁移方案。"
            "企业团队正在评估数据隔离、权限控制、稳定性、调用价格和监控能力。"
        ),
        category_id=tech.id,
        channel_id=channel.id,
        source_id="quality-primary-old",
        source_url="https://example.com/quality-primary-old",
        event_time=datetime(2026, 4, 20, 9, 0, 0),
        core_entity="OpenAI",
        detail_fetch_status="complete",
        detail_score=92,
        detail_content_length=120,
    )
    newer_weak = Info(
        title="OpenAI 新模型热议",
        content="OpenAI 新模型热议，网友继续讨论。",
        category_id=tech.id,
        channel_id=channel.id,
        source_id="quality-secondary-new",
        source_url="https://example.com/quality-secondary-new",
        event_time=datetime(2026, 4, 20, 9, 20, 0),
        core_entity="OpenAI",
        detail_fetch_status="partial",
        detail_score=58,
        detail_content_length=20,
    )
    session.add_all([older_quality, newer_weak])
    session.commit()

    rebuild_events(session)

    event = session.query(Event).filter(Event.title == "OpenAI 新模型完整分析").one()
    primary_link = session.query(EventItemLink).filter(EventItemLink.event_id == event.id, EventItemLink.is_primary == 1).one()
    assert primary_link.item_id == older_quality.id


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
    assert payload["summaries"]["heat_reason"]
    assert payload["summaries"]["risk_notice"]
    assert payload["summaries"]["source_compare"]
    assert payload["summaries"]["analysis_confidence"]
    assert len(payload["representative_sources"]) >= 1
    assert payload["representative_sources"][0]["quality_level"]
    assert payload["evidence_chain"]["usable_source_count"] >= 1
    assert payload["evidence_chain"]["evidence_sources"]
    assert payload["evidence_chain"]["platform_views"]
    assert payload["summaries"]["what_happened"] != payload["summaries"]["latest_update"]
    assert "推理" in payload["summaries"]["what_happened"] or "API" in payload["summaries"]["what_happened"]
    assert "OpenAI" in payload["summaries"]["why_it_matters"]
    assert "热点价值" in payload["summaries"]["heat_reason"]
    assert "持续校准" in payload["summaries"]["risk_notice"] or "暂未发现明显采集风险" in payload["summaries"]["risk_notice"]
    assert "分析可信度" in payload["summaries"]["analysis_confidence"]
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


def test_rebuild_events_groups_related_titles_by_semantic_entity(session):
    tech = Category(name="科技", code="tech", description="科技事件")
    session.add(tech)
    session.flush()

    juejin = Channel(
        name="掘金",
        code="juejin",
        base_url="https://juejin.cn",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    csdn = Channel(
        name="CSDN",
        code="csdn",
        base_url="https://csdn.net",
        category_id=tech.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add_all([juejin, csdn])
    session.flush()

    session.add_all(
        [
            Info(
                title="OpenAI 发布新模型能力",
                content="OpenAI 发布新模型后，开发者重点关注 API 接入节奏、推理性能和部署成本。" * 12,
                category_id=tech.id,
                channel_id=juejin.id,
                source_id="semantic-event-1",
                source_url="https://example.com/semantic-event-1",
                event_time=datetime(2026, 5, 8, 9, 0, 0),
                tech_entities="OpenAI,GPT-5",
                tech_keywords="API,推理",
                detail_fetch_status="complete",
                detail_score=90,
                detail_content_length=720,
            ),
            Info(
                title="OpenAI 新模型价格方案曝光",
                content="围绕 OpenAI 新模型价格方案，社区开始讨论调用成本、企业接入和模型推理效率。" * 12,
                category_id=tech.id,
                channel_id=csdn.id,
                source_id="semantic-event-2",
                source_url="https://example.com/semantic-event-2",
                event_time=datetime(2026, 5, 8, 9, 30, 0),
                tech_entities="OpenAI,GPT-5",
                tech_keywords="价格,推理",
                detail_fetch_status="complete",
                detail_score=88,
                detail_content_length=680,
            ),
        ]
    )
    session.commit()

    rebuild_events(session)

    event = session.query(Event).filter(Event.status == "active").one()
    assert event.source_count == 2
    assert "OpenAI" in event.title


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
    assert target["acquisition_quality"]["quality_level"]
    assert target["acquisition_quality"]["completeness_score"] > 0
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
    assert payload["acquisition_quality"]["summary"]
    assert payload["tech_entities"] == ["OpenAI", "MCP"]
    assert payload["tech_keywords"] == ["API", "开发工具"]

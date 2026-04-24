from datetime import datetime, timedelta

from cleaners import clean_info_list
from database import Category, Channel, Info
from scheduler import _save_crawled_data
from scheduler import _fetch_details_for_items
from crawlers.registry import crawler_registry
from services.detail_pipeline import DetailPipelineResult
from sql.init_data import init_mock_data
from services.data_maintenance import refresh_info_semantics
from crawlers.sports_utils import extract_article_text


def test_clean_info_list_removes_near_duplicate_title_and_content():
    now = datetime(2026, 4, 21, 10, 0, 0)
    items = [
        {
            "source_id": "source-a",
            "title": "OpenAI 发布新模型",
            "content": "OpenAI 发布新模型后，开发者重点关注 API 接入节奏和部署成本。",
            "source_url": "https://example.com/a",
            "event_time": now,
        },
        {
            "source_id": "source-b",
            "title": "OpenAI 发布新模型",
            "content": "OpenAI 发布新模型后，开发者重点关注 API 接入节奏和部署成本。",
            "source_url": "https://example.com/b",
            "event_time": now + timedelta(minutes=1),
        },
    ]

    cleaned = clean_info_list(items)

    assert len(cleaned) == 1
    assert cleaned[0]["source_id"] == "source-a"


def test_clean_info_list_filters_title_only_low_quality_items():
    cleaned = clean_info_list(
        [
            {
                "source_id": "source-a",
                "title": "OpenAI 发布新模型",
                "content": "OpenAI 发布新模型",
                "source_url": "https://example.com/a",
                "event_time": datetime(2026, 4, 21, 10, 0, 0),
            }
        ]
    )

    assert cleaned == []


def test_save_crawled_data_skips_existing_near_duplicate_content(session):
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
            title="OpenAI 发布新模型",
            content="OpenAI 发布新模型后，开发者重点关注 API 接入节奏和部署成本。",
            category_id=category.id,
            channel_id=channel.id,
            source_id="existing-a",
            source_url="https://example.com/existing-a",
            event_time=datetime(2026, 4, 21, 9, 0, 0),
        )
    )
    session.commit()

    saved_ids = _save_crawled_data(
        "36kr",
        [
            {
                "source_id": "new-duplicate",
                "title": "OpenAI 发布新模型",
                "content": "OpenAI 发布新模型后，开发者重点关注 API 接入节奏和部署成本。",
                "source_url": "https://example.com/new-duplicate",
                "event_time": datetime(2026, 4, 21, 10, 0, 0),
            }
        ],
    )

    assert saved_ids == []
    assert session.query(Info).count() == 1


def test_fetch_details_marks_title_duplicate_detail_as_low_quality(session, monkeypatch):
    category = Category(name="科技", code="tech", description="科技事件")
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
        content="列表摘要包含少量背景。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="detail-duplicate",
        source_url="https://example.com/detail-duplicate",
        event_time=datetime(2026, 4, 21, 9, 0, 0),
    )
    session.add(info)
    session.commit()
    info_id = info.id

    class DummyCrawler:
        def safe_fetch_detail(self, source_url, item):
            pipeline = DetailPipelineResult(
                content="OpenAI 发布新模型",
                status="complete",
                strategy="topic_search",
                score=88,
                content_length=12,
                failure_reason="",
                matched_rules=[],
            )
            return pipeline.content, pipeline.status, pipeline.failure_reason, pipeline

    crawler_registry.register("weibo", DummyCrawler())
    monkeypatch.setattr("scheduler.time.sleep", lambda _: None)
    monkeypatch.setattr("scheduler.random.uniform", lambda a, b: 0)

    _fetch_details_for_items("weibo", [info_id])

    refreshed = session.query(Info).filter(Info.id == info_id).first()
    assert refreshed.content == "列表摘要包含少量背景。"
    assert refreshed.detail_fetch_status == "list_only"
    assert refreshed.detail_fetch_error == "title_content_duplicate"


def test_sports_article_extraction_preserves_long_body_text():
    body = "中国女排在比赛中展现出稳定的一传、防守韧性和关键分把握能力。" * 90
    html = f'<html><body><div class="content_area"><p>{body}</p></div></body></html>'

    content = extract_article_text(html, [r'<div[^>]+class=["\'][^"\']*content_area[^"\']*["\'][^>]*>(.*?)</div>'])

    assert content == body
    assert len(content) > 500


def test_seed_data_populates_tech_semantic_fields(session):
    tech = Category(name="科技动向", code="tech", description="科技事件")
    ai = Category(name="AI大模型动向", code="ai", description="AI事件")
    hot = Category(name="热点事件", code="hot", description="热点事件")
    economy = Category(name="经济数据", code="economy", description="经济数据")
    international = Category(name="国际大事", code="international", description="国际大事")
    session.add_all([tech, ai, hot, economy, international])
    session.flush()

    channels = {}
    for code, category in [
        ("weibo", hot),
        ("toutiao", hot),
        ("xiaohongshu", hot),
        ("eastmoney", economy),
        ("reuters", international),
        ("csdn", tech),
        ("juejin", tech),
        ("cnblogs", tech),
        ("36kr", ai),
        ("zhihu", ai),
    ]:
        channel = Channel(
            name=code,
            code=code,
            base_url=f"https://example.com/{code}",
            category_id=category.id,
            crawl_interval=30,
            is_active=1,
        )
        session.add(channel)
        session.flush()
        channels[code] = channel.id

    init_mock_data(
        session,
        {
            "热点事件": hot.id,
            "经济数据": economy.id,
            "国际大事": international.id,
            "科技动向": tech.id,
            "AI大模型动向": ai.id,
        },
        channels,
    )

    ai_agent = session.query(Info).filter(Info.source_id == "mock_zh_001").first()
    assert ai_agent.tech_topic_type
    assert ai_agent.tech_keywords


def test_refresh_info_semantics_removes_stale_general_tech_and_populates_real_keywords(session):
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

    session.add_all(
        [
            Info(
                title="春日赏花攻略",
                content="全国多地进入赏花季，樱花、油菜花竞相绽放。",
                category_id=category.id,
                channel_id=channel.id,
                source_id="semantic-stale",
                source_url="https://example.com/semantic-stale",
                event_time=datetime(2026, 4, 21, 9, 0, 0),
                tech_topic_type="general_tech",
                tech_entities="旧实体",
                tech_keywords="旧关键词",
            ),
            Info(
                title="英伟达发布H200芯片",
                content="H200 芯片面向大模型训练场景，开发者开始讨论显存和训练效率。",
                category_id=category.id,
                channel_id=channel.id,
                source_id="semantic-real",
                source_url="https://example.com/semantic-real",
                event_time=datetime(2026, 4, 21, 9, 5, 0),
            ),
        ]
    )
    session.commit()

    result = refresh_info_semantics(session)

    stale = session.query(Info).filter(Info.source_id == "semantic-stale").first()
    real = session.query(Info).filter(Info.source_id == "semantic-real").first()
    assert result["processed_count"] == 2
    assert stale.tech_topic_type == ""
    assert stale.tech_entities == ""
    assert stale.tech_keywords == ""
    assert real.tech_topic_type == "chip_release"
    assert "英伟达" in real.tech_entities
    assert "显存" in real.tech_keywords

from datetime import datetime

from fastapi.testclient import TestClient

from api import app
from database import Category, Channel, Event, Info
from services.data_maintenance import archive_duplicate_title_infos, archive_low_quality_infos
from services.data_quality_report import build_data_quality_report


def _seed_category_and_channel(session):
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
    return category, channel


def test_build_data_quality_report_counts_duplicate_and_missing_fields(session):
    category, channel = _seed_category_and_channel(session)
    session.add_all(
        [
            Info(
                title="OpenAI 发布新模型",
                content="OpenAI 发布新模型",
                category_id=category.id,
                channel_id=channel.id,
                source_id="quality-001",
                source_url="https://example.com/a",
                event_time=datetime(2026, 4, 21, 9, 0, 0),
                detail_fetch_status="list_only",
                detail_score=10,
                detail_content_length=8,
            ),
            Info(
                title="OpenAI 发布新模型",
                content="OpenAI 新模型开放 API 接入，开发者正在讨论价格和推理能力。",
                category_id=category.id,
                channel_id=channel.id,
                source_id="quality-002",
                source_url="https://example.com/a",
                event_time=datetime(2026, 4, 21, 9, 30, 0),
                detail_fetch_status="complete",
                detail_score=90,
                detail_content_length=36,
                tech_topic_type="model_release",
                tech_entities="OpenAI",
                tech_keywords="API,推理",
            ),
        ]
    )
    session.add(
        Event(
            title="OpenAI 发布新模型",
            one_line_summary="OpenAI 发布新模型",
            primary_category_id=category.id,
            source_count=2,
        )
    )
    session.commit()

    report = build_data_quality_report(session)

    assert report["info"]["total"] == 2
    assert report["info"]["title_content_duplicate_count"] == 1
    assert report["info"]["duplicate_title_count"] == 1
    assert report["info"]["duplicate_source_url_count"] == 1
    assert report["info"]["semantic_scope_total"] == 2
    assert report["info"]["missing_semantic_count"] == 1
    assert report["event"]["title_summary_duplicate_count"] == 1
    assert report["recommendations"]
    assert report["samples"]["incomplete_details"][0]["source_id"] == "quality-001"
    assert report["samples"]["missing_semantics"][0]["source_id"] == "quality-001"


def test_admin_data_quality_report_api_returns_metrics(session):
    _seed_category_and_channel(session)
    session.commit()

    client = TestClient(app)
    response = client.get("/api/admin/data-quality-report")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["info"]["total"] == 0
    assert payload["event"]["total"] == 0
    assert payload["recommendations"] == ["当前核心质量指标健康，可以进入页面回归和真实采集压力测试。"]


def test_archive_low_quality_infos_soft_deletes_only_obvious_bad_records(session):
    category, channel = _seed_category_and_channel(session)
    bad_info = Info(
        title="OpenAI 发布新模型",
        content="OpenAI 发布新模型",
        category_id=category.id,
        channel_id=channel.id,
        source_id="archive-bad",
        source_url="https://example.com/archive-bad",
        event_time=datetime(2026, 4, 21, 9, 0, 0),
        detail_fetch_status="list_only",
        detail_score=5,
        detail_content_length=8,
    )
    good_info = Info(
        title="OpenAI API 价格调整",
        content="OpenAI API 价格调整后，开发者重点关注推理成本和模型接入节奏。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="archive-good",
        source_url="https://example.com/archive-good",
        event_time=datetime(2026, 4, 21, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=35,
        tech_topic_type="model_release",
        tech_entities="OpenAI",
        tech_keywords="API,推理",
    )
    session.add_all([bad_info, good_info])
    session.commit()

    result = archive_low_quality_infos(session)

    assert result == {"scanned_count": 2, "archived_count": 1}
    assert bad_info.is_deleted == 1
    assert good_info.is_deleted == 0
    assert build_data_quality_report(session)["info"]["total"] == 1


def test_archive_low_quality_infos_soft_deletes_javascript_shell_content(session):
    category, channel = _seed_category_and_channel(session)
    shell_info = Info(
        title="机器人半马见证大国创造澎湃动能",
        content="今日头条 您需要允许该网站执行 JavaScript",
        category_id=category.id,
        channel_id=channel.id,
        source_id="archive-shell",
        source_url="https://www.toutiao.com/trending/7630373183060770879/",
        event_time=datetime(2026, 4, 21, 9, 0, 0),
        detail_fetch_status="partial",
        detail_strategy="web_fallback",
        detail_score=38,
        detail_content_length=26,
    )
    session.add(shell_info)
    session.commit()

    result = archive_low_quality_infos(session)

    assert result == {"scanned_count": 1, "archived_count": 1}
    assert shell_info.is_deleted == 1


def test_admin_archive_low_quality_infos_api_rebuilds_quality_report(session):
    category, channel = _seed_category_and_channel(session)
    session.add(
        Info(
            title="英伟达发布H200芯片",
            content="英伟达发布H200芯片",
            category_id=category.id,
            channel_id=channel.id,
            source_id="archive-api-bad",
            source_url="https://example.com/archive-api-bad",
            event_time=datetime(2026, 4, 21, 9, 0, 0),
            detail_fetch_status="list_only",
            detail_score=5,
            detail_content_length=8,
        )
    )
    session.commit()

    client = TestClient(app)
    response = client.post("/api/admin/archive-low-quality")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["archived_count"] == 1
    assert payload["quality_report"]["info"]["total"] == 0


def test_admin_retry_low_quality_details_api_groups_records_by_channel(session, monkeypatch):
    category, channel = _seed_category_and_channel(session)
    weak_info = Info(
        title="OpenAI 讨论升温",
        content="OpenAI 讨论升温",
        category_id=category.id,
        channel_id=channel.id,
        source_id="retry-detail-weak",
        source_url="https://example.com/retry-detail-weak",
        event_time=datetime(2026, 4, 21, 9, 0, 0),
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=8,
    )
    strong_info = Info(
        title="芯片行业新进展",
        content=(
            "芯片行业新进展带来供应链和算力平台讨论，信息正文已经足够完整。"
            "报道进一步补充了产业链上下游、先进封装、云端推理和终端应用的多方观点，"
            "可以作为完整详情样例，不应该进入低完整详情重抓队列。"
        ),
        category_id=category.id,
        channel_id=channel.id,
        source_id="retry-detail-strong",
        source_url="https://example.com/retry-detail-strong",
        event_time=datetime(2026, 4, 21, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=95,
        detail_content_length=130,
        tech_entities="芯片",
        tech_keywords="供应链,算力",
    )
    session.add_all([weak_info, strong_info])
    session.commit()

    calls = []

    def fake_fetch_details(channel_code, info_ids):
        calls.append((channel_code, info_ids))
        return {"detail_success_count": len(info_ids), "detail_failed_count": 0}

    monkeypatch.setattr("scheduler._fetch_details_for_items", fake_fetch_details)

    client = TestClient(app)
    response = client.post("/api/admin/retry-low-quality-details?limit=10")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["selected_count"] == 1
    assert payload["detail_success_count"] == 1
    assert payload["detail_failed_count"] == 0
    assert calls == [("weibo", [weak_info.id])]


def test_archive_duplicate_title_infos_keeps_highest_quality_record(session):
    category, channel = _seed_category_and_channel(session)
    weak = Info(
        title="日本正式允许出口杀伤性武器",
        content="日本政策调整引发讨论。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="duplicate-weak",
        source_url="https://example.com/duplicate-weak",
        event_time=datetime(2026, 4, 21, 9, 0, 0),
        detail_fetch_status="partial",
        detail_score=60,
        detail_content_length=20,
    )
    strong = Info(
        title="日本正式允许出口杀伤性武器",
        content="日本正式允许出口杀伤性武器，相关政策调整引发国际媒体持续讨论。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="duplicate-strong",
        source_url="https://example.com/duplicate-strong",
        event_time=datetime(2026, 4, 21, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=93,
        detail_content_length=47,
    )
    session.add_all([weak, strong])
    session.commit()

    result = archive_duplicate_title_infos(session)

    assert result == {"duplicate_group_count": 1, "archived_count": 1}
    assert weak.is_deleted == 1
    assert strong.is_deleted == 0
    assert build_data_quality_report(session)["info"]["duplicate_title_count"] == 0

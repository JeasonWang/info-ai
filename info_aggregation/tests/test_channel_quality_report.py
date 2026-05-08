from datetime import datetime

from database import Category, Channel, Info
from services.channel_quality_report import build_channel_quality_report


def test_channel_quality_report_excludes_seed_and_surfaces_weak_samples(session, monkeypatch):
    monkeypatch.setattr(
        "services.channel_quality_report.build_credential_report",
        lambda channel_codes: {
            "weibo": {
                "channel_code": "weibo",
                "health": "missing_required",
                "missing_required": ["WEIBO_COOKIE"],
                "credentials": [],
            }
        },
    )
    category = Category(name="热点事件", code="hot")
    channel = Channel(name="微博", code="weibo", category_rel=category)
    session.add_all([category, channel])
    session.flush()

    session.add_all(
        [
            Info(
                title="完整事件",
                content="完整事件详情，包含足够多的上下文和讨论。",
                category_id=category.id,
                channel_id=channel.id,
                source_id="complete",
                source_url="https://example.com/complete",
                event_time=datetime.now(),
                detail_fetch_status="complete",
                detail_strategy="mobile_search",
                detail_score=82,
                detail_content_length=120,
            ),
            Info(
                title="弱事件",
                content="弱事件",
                category_id=category.id,
                channel_id=channel.id,
                source_id="weak",
                source_url="https://example.com/weak",
                event_time=datetime.now(),
                detail_fetch_status="failed",
                detail_strategy="web_fallback",
                detail_score=0,
                detail_content_length=0,
                detail_fetch_error="anti_crawl_blocked",
            ),
            Info(
                title="模拟数据",
                content="模拟详情",
                category_id=category.id,
                channel_id=channel.id,
                source_id="seed",
                source_url="https://example.com/seed",
                event_time=datetime.now(),
                detail_fetch_status="complete",
                detail_strategy="seed",
                detail_score=100,
                detail_content_length=200,
            ),
        ]
    )
    session.commit()

    report = build_channel_quality_report(session, sample_limit=3)
    row = report["channels"][0]

    assert row["real_count"] == 2
    assert row["seed_count"] == 1
    assert row["complete_count"] == 1
    assert row["needs_attention_count"] == 1
    assert row["weak_samples"][0]["title"] == "弱事件"
    assert row["weak_samples"][0]["quality_level"] == "unusable"
    assert row["weak_samples"][0]["recommended_action"] == "check_cookie_or_rendering_strategy"
    assert row["weak_samples"][0]["attention_priority"] == 95
    assert "Cookie" in row["weak_samples"][0]["quality_summary"]
    assert row["top_failure_reasons"][0] == {"reason": "anti_crawl_blocked", "count": 1}
    assert row["quality_rank_score"] > 0
    assert row["governance_advice"]
    assert any("WEIBO_COOKIE" in item for item in row["governance_advice"])

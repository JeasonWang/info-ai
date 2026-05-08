from datetime import datetime

from database import Category, Channel, Info
from services.acquisition_quality import build_acquisition_quality_profile


def _info(session, channel_code: str, **kwargs) -> Info:
    category = Category(name="科技", code="tech")
    channel = Channel(name=channel_code, code=channel_code, category_rel=category)
    session.add_all([category, channel])
    session.flush()
    defaults = {
        "title": "agent设计系统-大模型意图识别",
        "content": "本文介绍 Agent 多层意图识别的核心架构、请求分流、成本控制和生产实践。" * 20,
        "category_id": category.id,
        "channel_id": channel.id,
        "source_id": f"{channel_code}-quality-sample",
        "source_url": "https://example.com/article",
        "event_time": datetime(2026, 5, 8, 12, 0, 0),
        "detail_fetch_status": "complete",
        "detail_score": 88,
        "detail_content_length": 720,
        "tech_entities": "Agent",
        "tech_keywords": "意图识别,架构",
    }
    defaults.update(kwargs)
    info = Info(**defaults)
    session.add(info)
    session.commit()
    return info


def test_quality_profile_marks_complete_article_as_usable(session):
    info = _info(session, "juejin")

    profile = build_acquisition_quality_profile(info)

    assert profile.quality_level in {"excellent", "usable"}
    assert profile.usable is True
    assert profile.needs_attention is False
    assert profile.should_enqueue_detail_job is False
    assert profile.required_length >= 600


def test_quality_profile_requeues_short_article_even_with_medium_score(session):
    info = _info(
        session,
        "juejin",
        content="只有很短的一段 Agent 意图识别介绍。",
        detail_score=70,
        detail_content_length=24,
    )

    profile = build_acquisition_quality_profile(info)

    assert profile.needs_attention is True
    assert profile.should_enqueue_detail_job is True
    assert "below_channel_required_length" in profile.risk_reasons
    assert profile.recommended_action == "retry_full_article_detail"


def test_quality_profile_identifies_anti_crawl_shell(session):
    info = _info(
        session,
        "xiaohongshu",
        content="请先登录后查看更多内容",
        detail_fetch_status="failed",
        detail_fetch_error="anti_crawl_blocked",
        detail_score=0,
        detail_content_length=0,
    )

    profile = build_acquisition_quality_profile(info)

    assert profile.quality_level == "unusable"
    assert profile.should_enqueue_detail_job is True
    assert profile.recommended_action == "check_cookie_or_rendering_strategy"

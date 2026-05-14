from datetime import datetime

from database import Category, Channel, Event, EventItemLink, Info
from services.analysis.event_display_quality import (
    backfill_event_display_quality,
    evaluate_event_display_quality,
    _title_similarity,
)


def _seed_category_channel(session, channel_code="xiaohongshu"):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name=channel_code,
        code=channel_code,
        base_url=f"https://example.com/{channel_code}",
        category_id=category.id,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    return category, channel


def test_single_weak_social_source_is_monitoring_not_active(session):
    category, channel = _seed_category_channel(session, "xiaohongshu")
    info = Info(
        title="夏日辣妹美甲",
        content="互动：点赞2.8万",
        category_id=category.id,
        channel_id=channel.id,
        source_id="xhs-weak",
        source_url="https://example.com/xhs-weak",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=9,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "monitoring"
    assert quality.level == "weak"
    assert "single_weak_source" in quality.reasons
    assert "low_value_content" in quality.reasons


def test_multi_source_with_complete_source_is_active(session):
    category, channel = _seed_category_channel(session, "toutiao")
    complete = Info(
        title="广西公交车坠翻致3死5伤",
        content="广西梧州公交车坠翻事故已有官方通报，事故原因和救援进展得到多个渠道跟进。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="tt-good",
        source_url="https://example.com/tt-good",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=92,
        detail_content_length=39,
    )
    partial = Info(
        title="广西公交事故救援进展",
        content="现场救援和伤者治疗仍在推进，更多细节等待后续通报。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="tt-partial",
        source_url="https://example.com/tt-partial",
        event_time=datetime(2026, 5, 13, 10, 5, 0),
        detail_fetch_status="partial",
        detail_score=70,
        detail_content_length=27,
    )

    quality = evaluate_event_display_quality([complete, partial])

    assert quality.status == "active"
    assert quality.level in {"excellent", "good"}
    assert quality.score >= 70


def test_title_similarity_keeps_shared_public_event_anchors_related():
    assert _title_similarity("广西公交车坠翻致3死5伤", "广西梧州公交事故救援进展") >= 0.35
    assert _title_similarity("马化腾回应AI掉队", "于正回应白鹿争议") < 0.35


def test_complete_social_discussion_without_fact_signal_stays_monitoring(session):
    category, channel = _seed_category_channel(session, "weibo")
    info = Info(
        title="明星机场穿搭引热议",
        content="多位网友晒出现场照片并继续转发讨论，相关话题评论量持续上升，粉丝关注造型和后续行程。",
        category_id=category.id,
        channel_id=channel.id,
        channel=channel,
        source_id="weibo-social-only",
        source_url="https://example.com/weibo-social-only",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=86,
        detail_content_length=44,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "monitoring"
    assert "social_signal_without_fact_source" in quality.reasons


def test_complete_social_source_with_official_fact_signal_can_be_active(session):
    category, channel = _seed_category_channel(session, "weibo")
    info = Info(
        title="广西公交事故官方通报",
        content="广西梧州公交车坠翻事故已有官方通报，救援和伤者治疗正在推进，事故原因仍在调查。",
        category_id=category.id,
        channel_id=channel.id,
        channel=channel,
        source_id="weibo-official-fact",
        source_url="https://example.com/weibo-official-fact",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=41,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "active"
    assert "social_signal_without_fact_source" not in quality.reasons


def test_social_source_with_media_fact_signal_can_be_active(session):
    category, channel = _seed_category_channel(session, "weibo")
    info = Info(
        title="山火救援进展获媒体报道",
        content="央视记者报道称，当地消防和应急部门仍在山火现场救援，后续损失评估正在推进。",
        category_id=category.id,
        channel_id=channel.id,
        channel=channel,
        source_id="weibo-media-fact",
        source_url="https://example.com/weibo-media-fact",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=88,
        detail_content_length=38,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "active"
    assert "social_signal_without_fact_source" not in quality.reasons


def test_social_source_with_generic_response_word_stays_monitoring(session):
    category, channel = _seed_category_channel(session, "weibo")
    info = Info(
        title="演员回应新剧争议",
        content="演员回应新剧争议，粉丝和网友围绕剧情、造型和后续互动持续讨论。",
        category_id=category.id,
        channel_id=channel.id,
        channel=channel,
        source_id="weibo-generic-response",
        source_url="https://example.com/weibo-generic-response",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=88,
        detail_content_length=32,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "monitoring"
    assert "social_signal_without_fact_source" in quality.reasons


def test_social_source_with_cctv_recommendation_word_stays_monitoring(session):
    category, channel = _seed_category_channel(session, "xiaohongshu")
    info = Info(
        title="央视推荐夏日饮品",
        content="央视推荐夏日饮品，用户分享绿豆西米露做法和口味体验，评论区持续讨论。",
        category_id=category.id,
        channel_id=channel.id,
        channel=channel,
        source_id="xhs-cctv-recommendation",
        source_url="https://example.com/xhs-cctv-recommendation",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=35,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "monitoring"
    assert "social_signal_without_fact_source" in quality.reasons


def test_low_value_hot_title_stays_monitoring(session):
    category, channel = _seed_category_channel(session, "toutiao")
    info = Info(
        title="王皓儿子带鲜花接机爸爸",
        content="王皓儿子带鲜花接机爸爸，相关短视频引发讨论。",
        category_id=category.id,
        category=category,
        channel_id=channel.id,
        channel=channel,
        source_id="hot-low-value-title",
        source_url="https://example.com/hot-low-value-title",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=88,
        detail_content_length=28,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "monitoring"
    assert "low_value_content" in quality.reasons


def test_partial_source_without_complete_detail_explains_missing_complete_source(session):
    category, channel = _seed_category_channel(session, "toutiao")
    info = Info(
        title="景区突发排队拥堵",
        content="景区突发排队拥堵，现场游客反馈较多，管理方暂未发布完整情况说明。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="partial-missing-complete",
        source_url="https://example.com/partial-missing-complete",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="partial",
        detail_score=68,
        detail_content_length=35,
    )

    quality = evaluate_event_display_quality([info])

    assert quality.status == "monitoring"
    assert "missing_complete_source" in quality.reasons


def test_mixed_unrelated_sources_are_monitoring_even_with_fact_markers(session):
    category, channel = _seed_category_channel(session, "weibo")
    first = Info(
        title="马化腾回应AI掉队",
        content="微博热搜 马化腾回应AI掉队 正在持续发酵，当前背景包括：马化腾回应AI掉队；热榜分类：互联网。",
        category_id=category.id,
        channel_id=channel.id,
        channel=channel,
        source_id="weibo-mixed-first",
        source_url="https://example.com/weibo-mixed-first",
        event_time=datetime(2026, 5, 14, 8, 0, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=60,
    )
    second = Info(
        title="于正回应白鹿争议",
        content="微博热搜 于正回应白鹿争议 正在持续发酵，当前背景包括：于正回应白鹿争议；热榜分类：艺人。",
        category_id=category.id,
        channel_id=channel.id,
        channel=channel,
        source_id="weibo-mixed-second",
        source_url="https://example.com/weibo-mixed-second",
        event_time=datetime(2026, 5, 14, 8, 5, 0),
        detail_fetch_status="complete",
        detail_score=90,
        detail_content_length=60,
    )

    quality = evaluate_event_display_quality([first, second])

    assert quality.status == "monitoring"
    assert "mixed_unrelated_sources" in quality.reasons


def test_backfill_event_display_quality_updates_existing_events(session):
    category, xhs = _seed_category_channel(session, "xiaohongshu")
    toutiao = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://example.com/toutiao",
        category_id=category.id,
        is_active=1,
    )
    session.add(toutiao)
    session.flush()

    weak_info = Info(
        title="夏日辣妹美甲",
        content="互动：点赞2.8万",
        category_id=category.id,
        channel_id=xhs.id,
        source_id="xhs-backfill-weak",
        source_url="https://example.com/xhs-backfill-weak",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=9,
    )
    good_info = Info(
        title="广西公交车坠翻致3死5伤",
        content="广西梧州公交车坠翻事故已有官方通报，事故原因和救援进展得到多个渠道跟进。",
        category_id=category.id,
        channel_id=toutiao.id,
        source_id="tt-backfill-good",
        source_url="https://example.com/tt-backfill-good",
        event_time=datetime(2026, 5, 13, 10, 5, 0),
        detail_fetch_status="complete",
        detail_score=92,
        detail_content_length=39,
    )
    session.add_all([weak_info, good_info])
    session.flush()

    weak_event = Event(
        title="夏日辣妹美甲",
        one_line_summary="互动：点赞2.8万。",
        primary_category_id=category.id,
        status="active",
        source_count=1,
    )
    good_event = Event(
        title="广西公交车坠翻致3死5伤",
        one_line_summary="广西公交车坠翻事故已有官方通报。",
        primary_category_id=category.id,
        status="active",
        source_count=1,
    )
    session.add_all([weak_event, good_event])
    session.flush()
    session.add_all(
        [
            EventItemLink(event_id=weak_event.id, item_id=weak_info.id, role="primary", is_primary=1, weight=10),
            EventItemLink(event_id=good_event.id, item_id=good_info.id, role="primary", is_primary=1, weight=90),
        ]
    )
    session.commit()

    result = backfill_event_display_quality(session)
    session.refresh(weak_event)
    session.refresh(good_event)

    assert result["processed_count"] == 2
    assert result["changed_count"] == 2
    assert result["status_counts"]["monitoring"] == 1
    assert result["status_counts"]["active"] == 1
    assert weak_event.status == "monitoring"
    assert "low_value_content" in weak_event.display_quality_reason
    assert good_event.status == "active"
    assert good_event.display_quality_score >= 70

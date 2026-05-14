from datetime import datetime, timedelta

from database import (
    Category,
    Channel,
    Event,
    EventAnalysisRun,
    EventAnalysisSnapshot,
    EventFactSnapshot,
    EventItemLink,
    EventTimelineAnalysis,
    Info,
)
from services.event_analysis import analyze_event_sources
from services.analysis.event_builder import _reanalyze_existing_event, rebuild_events


def _seed_channel(session):
    category = Category(name="AI大模型动向", code="ai", description="AI")
    session.add(category)
    session.flush()
    channel = Channel(
        name="掘金",
        code="juejin",
        base_url="https://juejin.cn",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    return category, channel


def test_rule_analysis_removes_page_metadata_and_generates_natural_summary(session):
    category, channel = _seed_channel(session)
    item = Info(
        title="agent设计系统-大模型意图识别",
        content=(
            "皮皮大人 2026-05-08 25 阅读10分钟。"
            "0. 为什么需要“多层意图识别”？想象一下：你的 Agent 支持 50 多个技能。"
            "如果用户每说一句话，你都调用一次大模型去理解，会发生什么？"
            "成本爆炸：每天百万请求，GPT-4 级别模型一个月烧掉几万块。"
        ),
        category_id=category.id,
        channel_id=channel.id,
        source_id="juejin-agent",
        source_url="https://juejin.cn/post/agent",
        event_time=datetime(2026, 5, 8, 9, 0, 0),
        core_entity="Agent",
        tech_keywords="意图识别,成本优化",
        detail_fetch_status="complete",
        detail_score=90,
    )

    result = analyze_event_sources([item])

    assert "阅读10分钟" not in result.one_line_summary
    assert "皮皮大人" not in result.one_line_summary
    assert result.one_line_summary.endswith(("。", "！", "？"))
    assert result.one_line_summary != item.content[:120]
    assert "多层意图识别" in result.what_happened
    assert result.provider == "rule"
    assert result.timeline_points[0].summary.endswith(("。", "！", "？"))


def test_rule_analysis_caps_long_unpunctuated_one_line_summary(session):
    category, channel = _seed_channel(session)
    long_content = (
        "不少家长带未成年人观看景区展现海滨文化适不适合带娃观看是个人选择近日一段三亚千古情演出现场"
        "舞者身着比基尼表演的画面引热议视频中台下可清晰听到未成年人声音不少网友质疑作为面向全年龄段的"
        "商业演出存在争议记者搜索发现关于该段表演的争议并非近期才出现从2023年开始就有网友发布避雷帖"
        "称带孩子观看时感到尴尬作为三亚标志性的旅游演艺项目目前表演服装已调整"
    )
    item = Info(
        title="三亚千古情演出争议",
        content=long_content,
        category_id=category.id,
        channel_id=channel.id,
        source_id="long-one-line",
        source_url="https://example.com/long-one-line",
        event_time=datetime(2026, 5, 9, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=80,
    )

    result = analyze_event_sources([item])

    assert len(result.one_line_summary) <= 220
    assert result.one_line_summary.endswith(("。", "！", "？"))


def test_rule_analysis_does_not_use_low_value_interaction_text_as_summary(session):
    category, channel = _seed_channel(session)
    item = Info(
        title="夏日辣妹美甲",
        content="夏日辣妹美甲。互动：点赞2.8万",
        category_id=category.id,
        channel_id=channel.id,
        source_id="low-value-summary",
        source_url="https://example.com/low-value-summary",
        event_time=datetime(2026, 5, 13, 10, 0, 0),
        detail_fetch_status="list_only",
        detail_score=10,
    )

    result = analyze_event_sources([item])

    assert "互动：点赞" not in result.one_line_summary
    assert "热度线索" in result.one_line_summary
    assert "缺少完整事实来源" in result.what_happened


def test_rule_analysis_rewrites_hot_public_event_summary_from_noisy_source(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="浏阳烟花厂爆炸事故已有29人出院",
        content="浏阳烟花厂爆炸事故已有29人出院 湖南全力救治伤员 已有29名伤员出院 浏阳所有烟花厂老板要悲催了！",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-noisy-summary",
        source_url="https://example.com/hot-noisy-summary",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=92,
    )

    result = analyze_event_sources([item])

    assert "悲催" not in result.one_line_summary
    assert "公共安全" in result.one_line_summary
    assert result.one_line_summary.endswith("。")


def test_rule_analysis_rewrites_hot_policy_event_summary_from_commentary(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="特朗普访华有何核心诉求",
        content="特朗普正式开启第二次访华之旅，来自小舰长吕礼诗和晓娇的观察。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-policy-commentary",
        source_url="https://example.com/hot-policy-commentary",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=90,
    )

    result = analyze_event_sources([item])

    assert "小舰长" not in result.one_line_summary
    assert "公共政策" in result.one_line_summary


def test_rule_analysis_rewrites_hot_policy_meeting_summary(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="特朗普期待与中方会晤",
        content="特朗普期待与中方会晤，后续安排仍有待确认。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-policy-meeting",
        source_url="https://example.com/hot-policy-meeting",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=90,
    )

    result = analyze_event_sources([item])

    assert "今日头条已出现" not in result.one_line_summary
    assert "公共政策" in result.one_line_summary


def test_rule_analysis_rewrites_hot_accident_summary_from_title_marker(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="渔民坠海后失踪 救援仍在进行",
        content="渔民坠海后失踪，现场救援仍在进行，这咋回事？",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-accident-marker",
        source_url="https://example.com/hot-accident-marker",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=88,
    )

    result = analyze_event_sources([item])

    assert "咋回事" not in result.one_line_summary
    assert "公共安全" in result.one_line_summary


def test_rule_analysis_rewrites_hot_sports_summary_from_title_marker(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="马刺大胜对手 总分扳平进入季后赛半决赛",
        content="马刺大胜对手，总分扳平进入季后赛半决赛，流言板热议这咋回事？",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-sports-marker",
        source_url="https://example.com/hot-sports-marker",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=88,
    )

    result = analyze_event_sources([item])

    assert "流言板" not in result.one_line_summary
    assert "体育赛程" in result.one_line_summary


def test_rule_analysis_rewrites_hot_media_commentary_summary(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="媒体：公权力不该给物业合同做担保",
        content="媒体：公权力不该给物业合同做担保。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-media-commentary",
        source_url="https://example.com/hot-media-commentary",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=80,
    )

    result = analyze_event_sources([item])

    assert "今日头条已出现" not in result.one_line_summary
    assert "媒体视角" in result.one_line_summary


def test_rule_analysis_rewrites_hot_tech_emotional_summary(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="中科曙光发布高端全闪存存储",
        content="FlashNexus 9000 存储芯片又传来大利好！",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-tech-emotional",
        source_url="https://example.com/hot-tech-emotional",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=88,
    )

    result = analyze_event_sources([item])

    assert "大利好" not in result.one_line_summary
    assert "科技产业动态" in result.one_line_summary


def test_rule_analysis_rewrites_hot_fire_control_summary(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    item = Info(
        title="男子点燃柳絮后离开 消防迅速处置",
        content="男子点燃柳絮后离开，消防迅速处置。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="hot-fire-control",
        source_url="https://example.com/hot-fire-control",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=88,
    )

    result = analyze_event_sources([item])

    assert "今日头条已出现" not in result.one_line_summary
    assert "公共安全" in result.one_line_summary


def test_reanalyze_existing_event_refreshes_event_one_line_summary(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="今日头条",
        code="toutiao",
        base_url="https://www.toutiao.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()
    info = Info(
        title="浏阳烟花厂爆炸事故已有29人出院",
        content="浏阳烟花厂爆炸事故已有29人出院 湖南全力救治伤员 已有29名伤员出院 浏阳所有烟花厂老板要悲催了！",
        category_id=category.id,
        channel_id=channel.id,
        source_id="reanalyze-refresh-summary",
        source_url="https://example.com/reanalyze-refresh-summary",
        event_time=datetime(2026, 5, 14, 10, 0, 0),
        detail_fetch_status="complete",
        detail_score=92,
    )
    event = Event(
        title=info.title,
        one_line_summary="湖南全力救治浏阳华盛烟花厂爆炸事故伤员 已有29名伤员出院 浏阳所有烟花厂老板要悲催了！",
        primary_category_id=category.id,
        status="active",
        source_count=1,
    )
    session.add_all([info, event])
    session.flush()
    session.add(EventItemLink(event_id=event.id, item_id=info.id, role="primary", is_primary=1, weight=90))
    session.commit()

    assert _reanalyze_existing_event(session, event)

    assert "悲催" not in event.one_line_summary
    assert "公共安全" in event.one_line_summary


def test_rebuild_events_persists_analysis_runs_snapshots_and_timeline(session):
    category, channel = _seed_channel(session)
    now = datetime(2026, 5, 8, 9, 0, 0)
    session.add_all(
        [
            Info(
                title="Agent 意图识别方案发布",
                content="团队发布多层意图识别方案，用规则路由降低大模型调用成本，并提升复杂请求处理稳定性。",
                category_id=category.id,
                channel_id=channel.id,
                source_id="agent-1",
                source_url="https://example.com/agent-1",
                event_time=now,
                core_entity="Agent",
                tech_keywords="意图识别,成本优化",
                    detail_fetch_status="complete",
                detail_score=86,
            ),
            Info(
                title="Agent 意图识别方案实测",
                content="实测显示多层意图识别可以减少无效模型调用，用户请求会先经过规则判断再进入模型分析。",
                category_id=category.id,
                channel_id=channel.id,
                source_id="agent-2",
                source_url="https://example.com/agent-2",
                event_time=now + timedelta(minutes=20),
                core_entity="Agent",
                tech_keywords="意图识别,请求路由",
                    detail_fetch_status="complete",
                detail_score=82,
            ),
        ]
    )
    session.commit()

    rebuild_events(session)

    run = session.query(EventAnalysisRun).one()
    assert run.status == "succeeded"
    assert run.provider == "rule"
    assert run.fallback_used == 0
    assert session.query(EventFactSnapshot).count() >= 2
    assert session.query(EventAnalysisSnapshot).filter_by(analysis_type="what_happened").count() == 1
    timeline = session.query(EventTimelineAnalysis).order_by(EventTimelineAnalysis.display_order).all()
    assert len(timeline) == 2
    assert all(entry.summary.endswith(("。", "！", "？")) for entry in timeline)

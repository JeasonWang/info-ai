from datetime import datetime, timedelta

from database import (
    Category,
    Channel,
    EventAnalysisRun,
    EventAnalysisSnapshot,
    EventFactSnapshot,
    EventTimelineAnalysis,
    Info,
)
from services.event_analysis import analyze_event_sources
from services.analysis.event_builder import rebuild_events


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

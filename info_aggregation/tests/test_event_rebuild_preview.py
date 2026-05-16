from datetime import datetime

from database import Category, Channel, Event, Info
from tools.event_rebuild_preview import preview_event_rebuild


def test_event_rebuild_preview_reports_grouping_and_risk_samples(session):
    category = Category(name="热点", code="hot")
    weibo = Channel(name="微博", code="weibo", category_rel=category)
    toutiao = Channel(name="今日头条", code="toutiao", category_rel=category)
    session.add_all([category, weibo, toutiao])
    session.flush()

    session.add_all(
        [
            Info(
                title="广西公交车坠翻致3死5伤",
                content="广西梧州一辆公交车发生坠翻事故，当地通报已有人员伤亡，救援和原因调查正在推进。",
                category_id=category.id,
                channel_id=weibo.id,
                source_id="preview-1",
                event_time=datetime(2026, 5, 14, 9, 0, 0),
                detail_fetch_status="complete",
                detail_score=90,
                detail_content_length=42,
            ),
            Info(
                title="广西梧州公交事故救援进展",
                content="广西梧州公交事故救援持续进行，伤者治疗和事故原因调查成为后续关注重点。",
                category_id=category.id,
                channel_id=toutiao.id,
                source_id="preview-2",
                event_time=datetime(2026, 5, 14, 9, 5, 0),
                detail_fetch_status="complete",
                detail_score=90,
                detail_content_length=36,
            ),
            Info(
                title="单平台热梗一",
                content="社交平台用户围绕一个轻娱乐话题展开讨论。",
                category_id=category.id,
                channel_id=weibo.id,
                source_id="preview-3",
                event_time=datetime(2026, 5, 14, 9, 10, 0),
                core_entity="单平台热梗",
                detail_fetch_status="complete",
                detail_score=85,
                detail_content_length=30,
            ),
            Info(
                title="单平台热梗二",
                content="社交平台用户继续围绕另一个轻娱乐话题讨论。",
                category_id=category.id,
                channel_id=weibo.id,
                source_id="preview-4",
                event_time=datetime(2026, 5, 14, 9, 11, 0),
                core_entity="单平台热梗",
                detail_fetch_status="complete",
                detail_score=85,
                detail_content_length=30,
            ),
            Info(
                title="单平台热梗三",
                content="社交平台用户继续围绕第三个轻娱乐话题讨论。",
                category_id=category.id,
                channel_id=weibo.id,
                source_id="preview-5",
                event_time=datetime(2026, 5, 14, 9, 12, 0),
                core_entity="单平台热梗",
                detail_fetch_status="complete",
                detail_score=85,
                detail_content_length=30,
            ),
        ]
    )
    session.add(Event(title="广西公交事故", event_key="unused", primary_category_id=category.id, status="active"))
    session.commit()

    report = preview_event_rebuild(session, limit=10)

    assert report["sampled_info_count"] == 5
    assert report["candidate_group_count"] == 2
    assert report["multi_source_group_count"] >= 1
    assert report["sample_groups"][0]["anchor"]
    assert "risk_groups" in report
    assert report["risk_groups"][0]["anchor"] == "单平台热梗"

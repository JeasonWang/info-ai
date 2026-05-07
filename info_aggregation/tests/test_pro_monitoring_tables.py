from datetime import datetime

from database import (
    Category,
    Channel,
    CrawlRunLog,
    CrawlTask,
    DataQualitySnapshot,
    Info,
)
from scheduler import _record_crawl_run, _sync_crawl_tasks
from services.data_quality_report import save_data_quality_snapshot


def test_record_crawl_run_persists_scheduler_metrics(session):
    started_at = datetime(2026, 4, 22, 10, 0, 0)
    finished_at = datetime(2026, 4, 22, 10, 1, 0)

    _record_crawl_run(
        session,
        channel_code="weibo",
        trigger_type="scheduler",
        status="success",
        raw_count=10,
        cleaned_count=8,
        saved_count=3,
        detail_success_count=2,
        detail_failed_count=1,
        error_message="",
        started_at=started_at,
        finished_at=finished_at,
    )

    row = session.query(CrawlRunLog).one()
    assert row.channel_code == "weibo"
    assert row.saved_count == 3
    assert row.detail_success_count == 2
    assert row.detail_failed_count == 1
    assert row.started_at == started_at
    assert row.finished_at == finished_at


def test_save_data_quality_snapshot_uses_report_metrics(session):
    category = Category(name="科技", code="tech", description="科技事件")
    session.add(category)
    session.flush()
    channel = Channel(
        name="微博",
        code="weibo",
        base_url="https://weibo.com",
        category_id=category.id,
    )
    session.add(channel)
    session.flush()
    session.add(
        Info(
            title="OpenAI 发布新模型",
            content="OpenAI 发布新模型",
            category_id=category.id,
            channel_id=channel.id,
            source_id="snapshot-001",
            source_url="https://example.com/a",
            detail_fetch_status="list_only",
            detail_score=10,
            detail_content_length=8,
        )
    )
    session.commit()

    snapshot = save_data_quality_snapshot(session, category_code="all")

    assert snapshot.total_count == 1
    assert snapshot.empty_content_count == 0
    assert snapshot.low_detail_score_count == 1
    assert snapshot.missing_entity_count == 1
    assert "recommendations" in snapshot.snapshot_payload


def test_sync_crawl_tasks_creates_tasks_for_active_channels(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    session.add(
        Channel(
            name="微博",
            code="weibo",
            base_url="https://weibo.com",
            category_id=category.id,
            crawl_interval=30,
            is_active=1,
        )
    )
    session.commit()

    result = _sync_crawl_tasks(session)

    assert result == {"created_count": 1, "updated_count": 0}
    task = session.query(CrawlTask).one()
    assert task.task_code == "crawl_weibo"
    assert task.task_name == "微博采集"
    assert task.schedule_value == "30"
    assert task.status == "active"


def test_channel_schedule_config_is_exposed_for_admin(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="微博",
        code="weibo",
        base_url="https://weibo.com",
        category_id=category.id,
        crawl_interval=30,
        base_interval_minutes=20,
        hot_interval_minutes=5,
        min_interval_minutes=3,
        max_interval_minutes=120,
        manual_interval_enabled=1,
        effective_interval_minutes=5,
        schedule_version=4,
        is_active=1,
    )
    session.add(channel)
    session.commit()

    payload = channel.to_dict()

    assert payload["base_interval_minutes"] == 20
    assert payload["hot_interval_minutes"] == 5
    assert payload["min_interval_minutes"] == 3
    assert payload["max_interval_minutes"] == 120
    assert payload["manual_interval_enabled"] == 1
    assert payload["effective_interval_minutes"] == 5
    assert payload["schedule_version"] == 4


def test_sync_crawl_tasks_uses_effective_interval(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    session.add(
        Channel(
            name="微博",
            code="weibo",
            base_url="https://weibo.com",
            category_id=category.id,
            crawl_interval=30,
            effective_interval_minutes=5,
            is_active=1,
        )
    )
    session.commit()

    _sync_crawl_tasks(session)

    task = session.query(CrawlTask).one()
    assert task.schedule_value == "5"


def test_sync_crawl_tasks_refreshes_next_run_at_when_schedule_version_changes(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="微博",
        code="weibo",
        base_url="https://weibo.com",
        category_id=category.id,
        crawl_interval=30,
        effective_interval_minutes=30,
        schedule_version=1,
        is_active=1,
    )
    session.add(channel)
    session.commit()

    _sync_crawl_tasks(session)
    task = session.query(CrawlTask).one()
    first_next_run_at = task.next_run_at

    channel.effective_interval_minutes = 5
    channel.schedule_version = 2
    session.commit()
    result = _sync_crawl_tasks(session)

    session.refresh(task)
    assert result["updated_count"] == 1
    assert task.schedule_value == "5"
    assert task.schedule_version == 2
    assert task.next_run_at != first_next_run_at

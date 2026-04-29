from database import Category, Channel, DetailJob, Info
from services.detail_jobs import enqueue_low_quality_detail_jobs


def _seed_channel(session):
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
    return category, channel


def test_enqueue_low_quality_detail_jobs_creates_pending_jobs(session):
    category, channel = _seed_channel(session)
    session.add(
        Info(
            title="OpenAI 发布新模型",
            content="OpenAI 发布新模型",
            category_id=category.id,
            channel_id=channel.id,
            source_id="detail-job-001",
            source_url="https://example.com/a",
            detail_fetch_status="list_only",
            detail_score=10,
            detail_content_length=8,
        )
    )
    session.commit()

    result = enqueue_low_quality_detail_jobs(session, limit=20)

    assert result == {"created_count": 1, "skipped_count": 0}
    job = session.query(DetailJob).one()
    assert job.status == "pending"
    assert job.priority == 80
    assert job.attempt_count == 0
    assert job.channel_code == "36kr"
    assert job.last_failure_reason == "low_detail_score"


def test_enqueue_low_quality_detail_jobs_skips_existing_open_job(session):
    category, channel = _seed_channel(session)
    info = Info(
        title="OpenAI 发布新模型",
        content="OpenAI 发布新模型",
        category_id=category.id,
        channel_id=channel.id,
        source_id="detail-job-002",
        source_url="https://example.com/b",
        detail_fetch_status="failed",
        detail_score=0,
        detail_content_length=0,
    )
    session.add(info)
    session.flush()
    session.add(DetailJob(info_id=info.id, channel_code="36kr", status="pending", priority=80))
    session.commit()

    result = enqueue_low_quality_detail_jobs(session, limit=20)

    assert result == {"created_count": 0, "skipped_count": 1}
    assert session.query(DetailJob).count() == 1

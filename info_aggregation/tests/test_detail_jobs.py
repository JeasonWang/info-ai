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
    assert job.priority == 84
    assert job.attempt_count == 0
    assert job.channel_code == "36kr"
    assert job.last_failure_reason == "detail_list_only"


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


def test_enqueue_low_quality_detail_jobs_reuses_existing_failed_job(session):
    category, channel = _seed_channel(session)
    info = Info(
        title="OpenAI 发布新模型",
        content="OpenAI 发布新模型",
        category_id=category.id,
        channel_id=channel.id,
        source_id="detail-job-003",
        source_url="https://example.com/c",
        detail_fetch_status="failed",
        detail_score=0,
        detail_content_length=0,
    )
    session.add(info)
    session.flush()
    failed_job = DetailJob(
        info_id=info.id,
        channel_code="36kr",
        status="failed",
        priority=20,
        attempt_count=3,
        last_failure_reason="empty_content",
    )
    session.add(failed_job)
    session.commit()

    result = enqueue_low_quality_detail_jobs(session, limit=20)

    assert result == {"created_count": 1, "skipped_count": 0}
    assert session.query(DetailJob).count() == 1
    job = session.get(DetailJob, failed_job.id)
    assert job.status == "pending"
    assert job.priority == 88
    assert job.attempt_count == 0
    assert job.last_failure_reason == "detail_failed"


def test_enqueue_low_quality_detail_jobs_requeues_short_article_even_with_medium_score(session):
    category, channel = _seed_channel(session)
    short_article = "本文介绍 Agent 意图识别架构，但只有很短一段。"
    session.add(
        Info(
            title="agent设计系统-大模型意图识别",
            content=short_article,
            category_id=category.id,
            channel_id=channel.id,
            source_id="detail-job-short-article",
            source_url="https://example.com/short-article",
            detail_fetch_status="complete",
            detail_score=70,
            detail_content_length=len(short_article),
        )
    )
    session.commit()

    result = enqueue_low_quality_detail_jobs(session, limit=20)

    assert result == {"created_count": 1, "skipped_count": 0}
    job = session.query(DetailJob).one()
    assert job.last_failure_reason == "below_channel_required_length"
    assert job.priority == 76

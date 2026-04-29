from database import Category, Channel, DetailJob, Info
from crawlers.registry import crawler_registry
from services.detail_job_worker import crawler_detail_runner, process_pending_detail_jobs
from services.detail_pipeline import DetailPipelineResult


def _seed_detail_job(session):
    category = Category(name="科技", code="tech", description="科技事件")
    session.add(category)
    session.flush()
    channel = Channel(name="36氪", code="36kr", base_url="https://36kr.com", category_id=category.id)
    session.add(channel)
    session.flush()
    info = Info(
        title="OpenAI 发布新模型",
        content="OpenAI 发布新模型",
        category_id=category.id,
        channel_id=channel.id,
        source_id="worker-001",
        source_url="https://example.com/a",
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=8,
    )
    session.add(info)
    session.flush()
    job = DetailJob(info_id=info.id, channel_code="36kr", status="pending", priority=80)
    session.add(job)
    session.commit()
    return info.id, job.id


def test_process_pending_detail_jobs_marks_success_and_updates_info(session):
    info_id, job_id = _seed_detail_job(session)

    def runner(info):
        return DetailPipelineResult(
            content="OpenAI 发布新模型，开发者关注推理能力、API 接入节奏和企业落地成本。",
            status="complete",
            strategy="html_article",
            score=92,
            content_length=38,
            failure_reason="",
            matched_rules=[],
        )

    result = process_pending_detail_jobs(session, runner=runner, limit=5)

    assert result == {"succeeded_count": 1, "failed_count": 0}
    info = session.get(Info, info_id)
    job = session.get(DetailJob, job_id)
    assert info.detail_fetch_status == "complete"
    assert info.detail_score == 92
    assert info.detail_strategy == "html_article"
    assert job.status == "succeeded"
    assert job.attempt_count == 1


def test_process_pending_detail_jobs_retries_failed_job(session):
    _, job_id = _seed_detail_job(session)

    def runner(info):
        return DetailPipelineResult(
            content="",
            status="failed",
            strategy="html_article",
            score=0,
            content_length=0,
            failure_reason="empty_content",
            matched_rules=["empty_content"],
        )

    result = process_pending_detail_jobs(session, runner=runner, limit=5)

    assert result == {"succeeded_count": 0, "failed_count": 1}
    job = session.get(DetailJob, job_id)
    assert job.status == "pending"
    assert job.attempt_count == 1
    assert job.last_failure_reason == "empty_content"
    assert job.next_run_at is not None


class FakeCrawler:
    def safe_fetch_detail(self, source_url, item):
        pipeline = DetailPipelineResult(
            content="OpenAI 发布新模型，开发者关注推理能力、API 接入节奏和企业落地成本。",
            status="complete",
            strategy="fake_crawler",
            score=91,
            content_length=36,
            failure_reason="",
            matched_rules=[],
        )
        return pipeline.content, pipeline.status, pipeline.failure_reason, pipeline


def test_crawler_detail_runner_uses_registered_crawler(session):
    info_id, _ = _seed_detail_job(session)
    crawler_registry.register("36kr", FakeCrawler())

    result = crawler_detail_runner(session.get(Info, info_id))

    assert result.status == "complete"
    assert result.strategy == "fake_crawler"
    assert result.score == 91


class FailingCrawler:
    def safe_fetch_detail(self, source_url, item):
        pipeline = DetailPipelineResult(
            content="",
            status="failed",
            strategy="fake_crawler",
            score=0,
            content_length=0,
            failure_reason="empty_content",
            matched_rules=["empty_content"],
        )
        return "", pipeline.status, pipeline.failure_reason, pipeline


def test_crawler_detail_runner_uses_http_html_fallback_when_crawler_fails(session):
    info_id, _ = _seed_detail_job(session)
    crawler_registry.register("36kr", FailingCrawler())

    result = crawler_detail_runner(
        session.get(Info, info_id),
        html_fetcher=lambda url: """
        <article>
          <p>OpenAI 发布新模型，开发者关注推理能力、API 接入节奏、部署成本和企业落地节奏。</p>
        </article>
        """,
    )

    assert result.status == "complete"
    assert result.strategy == "http_html_article"

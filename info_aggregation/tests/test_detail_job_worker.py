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


def test_process_pending_detail_jobs_merges_when_failed_job_already_exists(session):
    info_id, pending_job_id = _seed_detail_job(session)
    existing_failed = DetailJob(
        info_id=info_id,
        channel_code="36kr",
        status="failed",
        priority=80,
        attempt_count=3,
        max_attempts=3,
        last_failure_reason="previous_failure",
    )
    session.add(existing_failed)
    pending_job = session.get(DetailJob, pending_job_id)
    pending_job.max_attempts = 1
    session.commit()

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
    pending_job = session.get(DetailJob, pending_job_id)
    failed_job = session.get(DetailJob, existing_failed.id)
    assert pending_job.status == f"merged_{pending_job_id}"
    assert pending_job.last_failure_reason == "merged_into_existing_failed_job"
    assert failed_job.status == "failed"
    assert failed_job.last_failure_reason == "empty_content"
    assert failed_job.attempt_count == 3


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
          <p>公司表示，新模型会进入企业客户试用阶段，并围绕产品能力、商业落地、市场增长和生态合作继续扩展。</p>
          <p>多家企业正在评估调用价格、稳定性、模型治理、数据隔离、权限控制和区域合规方案。</p>
          <p>行业分析人士认为，这会影响 AI 基础设施、云服务采购、软件集成和自动化办公产品的商业竞争。</p>
          <p>开发者关注 SDK、文档、错误处理、上下文窗口、吞吐量和监控能力，企业则关注服务等级协议和长期稳定性。</p>
          <p>如果后续产品表现稳定，更多行业客户可能把 AI 能力嵌入核心流程，带动咨询实施、数据治理和应用生态增长。</p>
          <p>报道进一步分析，商业软件厂商会把新模型能力包装进办公、客服、研发、数据分析和知识管理产品。</p>
          <p>云服务厂商也会围绕算力、存储、网络、安全审计和模型监控提供配套能力，帮助企业降低上线风险。</p>
          <p>投资者则会观察客户增长、续费率、毛利率和生态合作进展，判断这项产品是否能够形成长期商业壁垒。</p>
          <p>从市场角度看，AI 产品竞争已经从单点模型能力转向完整解决方案，企业会更关注稳定交付和真实业务收益。</p>
          <p>这也会推动更多公司重新评估预算、组织流程和数据资产治理。</p>
        </article>
        """,
    )

    assert result.status == "complete"
    assert result.strategy == "http_html_article"

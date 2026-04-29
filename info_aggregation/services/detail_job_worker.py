from collections.abc import Callable
from datetime import datetime, timedelta

from database import DetailJob, Info, InfoAcquisitionLog
from crawlers.registry import crawler_registry
from services.detail_pipeline import DetailPipelineResult
from services.detail_strategy_chain import DetailContext, DetailStrategyChain
from services.http_html_detail_strategy import HttpHtmlDetailStrategy


DetailRunner = Callable[[Info], DetailPipelineResult]


def crawler_detail_runner(info: Info, html_fetcher=None) -> DetailPipelineResult:
    """使用已注册渠道爬虫执行详情补偿，供 scheduler 默认调用。"""

    channel_code = info.channel.code if info.channel else ""
    crawler = crawler_registry.get(channel_code)
    if not crawler:
        return DetailPipelineResult(
            content="",
            status="failed",
            strategy="crawler_registry",
            score=0,
            content_length=0,
            failure_reason="crawler_not_registered",
            matched_rules=["crawler_not_registered"],
        )

    detail_content, status, error_msg, pipeline = crawler.safe_fetch_detail(
        info.source_url,
        info.to_dict(),
    )
    pipeline.content = detail_content or pipeline.content
    pipeline.status = status
    pipeline.failure_reason = error_msg or pipeline.failure_reason
    pipeline.content_length = len(pipeline.content or "")
    if pipeline.status in {"complete", "partial"} and pipeline.content and pipeline.score >= 60:
        return pipeline

    return DetailStrategyChain([HttpHtmlDetailStrategy(fetcher=html_fetcher)]).run(
        DetailContext(
            title=info.title,
            list_content=info.content or "",
            source_url=info.source_url,
            channel_code=channel_code,
            info_id=info.id,
            last_failure_reason=pipeline.failure_reason,
        )
    )


def _retry_delay(attempt_count: int) -> timedelta:
    return timedelta(minutes=min(60, 5 * max(1, attempt_count)))


def _apply_success(info: Info, job: DetailJob, result: DetailPipelineResult):
    info.content = result.content or info.content
    info.detail_fetch_status = result.status
    info.detail_fetch_error = result.failure_reason
    info.detail_strategy = result.strategy
    info.detail_score = result.score
    info.detail_content_length = result.content_length
    info.detail_fetched_at = datetime.now()
    job.status = "succeeded"
    job.last_failure_reason = ""


def _apply_failure(job: DetailJob, result: DetailPipelineResult):
    job.last_failure_reason = result.failure_reason or "detail_unavailable"
    if job.attempt_count >= job.max_attempts:
        job.status = "failed"
        return
    job.status = "pending"
    job.next_run_at = datetime.now() + _retry_delay(job.attempt_count)


def process_pending_detail_jobs(session, runner: DetailRunner, limit: int = 20) -> dict:
    """执行待补偿详情任务，并更新任务状态、Info 详情字段和采集日志。"""

    now = datetime.now()
    jobs = (
        session.query(DetailJob)
        .filter(DetailJob.status == "pending", DetailJob.next_run_at <= now)
        .order_by(DetailJob.priority.desc(), DetailJob.next_run_at.asc(), DetailJob.id.asc())
        .limit(limit)
        .all()
    )
    succeeded_count = 0
    failed_count = 0

    for job in jobs:
        info = session.get(Info, job.info_id)
        if not info:
            job.status = "cancelled"
            continue

        job.status = "running"
        job.attempt_count += 1
        result = runner(info)

        if result.status in {"complete", "partial"} and result.content:
            _apply_success(info, job, result)
            succeeded_count += 1
        else:
            _apply_failure(job, result)
            failed_count += 1

        session.add(
            InfoAcquisitionLog(
                info_id=info.id,
                channel_code=job.channel_code,
                strategy=result.strategy,
                status=result.status,
                score=result.score,
                content_length=result.content_length,
                failure_reason=result.failure_reason,
                matched_rules=",".join(result.matched_rules),
                raw_excerpt=(result.content or info.content or "")[:200],
            )
        )

    session.commit()
    return {"succeeded_count": succeeded_count, "failed_count": failed_count}

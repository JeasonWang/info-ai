import time
import random
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import func

from config import DETAIL_JOB_RUNNING_TIMEOUT_MINUTES
from database import DetailJob, Info, InfoAcquisitionLog
from crawlers.registry import crawler_registry
from services.collection.credential_provider import build_credential_report
from services.collection.detail_pipeline import DetailPipelineResult
from services.collection.detail_strategy_chain import DetailContext, DetailStrategyChain
from services.collection.http_html_detail_strategy import HttpHtmlDetailStrategy
from services.collection.secondary_search_detail_strategy import (
    SecondarySearchDetailStrategy,
    WeiboSecondarySearchDetailStrategy,
    XiaohongshuSecondarySearchDetailStrategy,
    ZhihuSecondarySearchDetailStrategy,
)
from services.analysis.event_analysis_reanalysis import mark_event_analysis_stale_for_info


DetailRunner = Callable[..., DetailPipelineResult]

STRICT_DETAIL_STRATEGY_HINTS = {
    "retry_full_article_detail",
    "search_secondary_detail_source",
    "check_cookie_or_rendering_strategy",
}


_CRAWLER_REGISTRY_BOOTSTRAPPED = False


def _ensure_crawler_registry_bootstrapped() -> None:
    """详情补偿 worker 可能由命令入口直接调用，需要自愈式注册爬虫。"""

    global _CRAWLER_REGISTRY_BOOTSTRAPPED
    if crawler_registry.list_channels():
        _CRAWLER_REGISTRY_BOOTSTRAPPED = True
        return
    if _CRAWLER_REGISTRY_BOOTSTRAPPED:
        return
    try:
        from application.crawler_bootstrap import register_all_crawlers

        register_all_crawlers()
        _CRAWLER_REGISTRY_BOOTSTRAPPED = True
    except Exception:
        _CRAWLER_REGISTRY_BOOTSTRAPPED = False


def _mark_strategy_hint(result: DetailPipelineResult, strategy_hint: str) -> DetailPipelineResult:
    if strategy_hint and f"strategy_hint:{strategy_hint}" not in result.matched_rules:
        result.matched_rules.append(f"strategy_hint:{strategy_hint}")
    return result


def _is_usable_detail_result(result: DetailPipelineResult, strategy_hint: str = "") -> bool:
    if not result.content:
        return False
    if result.status == "complete":
        return True
    if result.status == "partial" and strategy_hint not in STRICT_DETAIL_STRATEGY_HINTS and result.score >= 60:
        return True
    return False


def _credential_diagnostic_result(channel_code: str, strategy_hint: str) -> DetailPipelineResult | None:
    if strategy_hint != "check_cookie_or_rendering_strategy":
        return None
    report = build_credential_report([channel_code]).get(channel_code, {})
    missing_required = report.get("missing_required") or []
    if missing_required:
        return _mark_strategy_hint(
            DetailPipelineResult(
                content="",
                status="failed",
                strategy="credential_diagnostic",
                score=0,
                content_length=0,
                failure_reason="missing_required_credentials",
                matched_rules=[f"missing_credential:{name}" for name in missing_required],
            ),
            strategy_hint,
        )
    return None


def _secondary_strategy_for_channel(channel_code: str, html_fetcher=None, search_fetcher=None):
    strategy_map = {
        "zhihu": ZhihuSecondarySearchDetailStrategy,
        "xiaohongshu": XiaohongshuSecondarySearchDetailStrategy,
        "weibo": WeiboSecondarySearchDetailStrategy,
    }
    strategy_cls = strategy_map.get(channel_code, SecondarySearchDetailStrategy)
    return strategy_cls(search_fetcher=search_fetcher, article_fetcher=html_fetcher)


def crawler_detail_runner(
    info: Info,
    html_fetcher=None,
    strategy_hint: str = "",
    search_fetcher=None,
) -> DetailPipelineResult:
    """使用已注册渠道爬虫执行详情补偿，供 scheduler 默认调用。"""

    channel_code = info.channel.code if info.channel else ""
    diagnostic_result = _credential_diagnostic_result(channel_code, strategy_hint)
    if diagnostic_result:
        return diagnostic_result

    _ensure_crawler_registry_bootstrapped()
    crawler = crawler_registry.get(channel_code)
    if not crawler:
        return _mark_strategy_hint(
            DetailPipelineResult(
                content="",
                status="failed",
                strategy="crawler_registry",
                score=0,
                content_length=0,
                failure_reason="crawler_not_registered",
                matched_rules=["crawler_not_registered"],
            ),
            strategy_hint,
        )

    with crawler_registry.get_lock(channel_code):
        detail_content, status, error_msg, pipeline = crawler.safe_fetch_detail(
            info.source_url,
            info.to_dict(),
        )
    pipeline.content = detail_content or pipeline.content
    pipeline.status = status
    pipeline.failure_reason = error_msg or pipeline.failure_reason
    pipeline.content_length = len(pipeline.content or "")
    pipeline = _mark_strategy_hint(pipeline, strategy_hint)
    if _is_usable_detail_result(pipeline, strategy_hint):
        return pipeline

    fallback_strategies = []
    if strategy_hint == "search_secondary_detail_source":
        fallback_strategies.append(
            _secondary_strategy_for_channel(channel_code, html_fetcher=html_fetcher, search_fetcher=search_fetcher)
        )
    fallback_strategies.append(HttpHtmlDetailStrategy(fetcher=html_fetcher))
    fallback_result = DetailStrategyChain(fallback_strategies).run(
        DetailContext(
            title=info.title,
            list_content=info.content or "",
            source_url=info.source_url,
            channel_code=channel_code,
            info_id=info.id,
            last_failure_reason=pipeline.failure_reason,
            strategy_hint=strategy_hint,
        )
    )
    return _mark_strategy_hint(fallback_result, strategy_hint)


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


def _merge_into_existing_failed_job(session, job: DetailJob, result: DetailPipelineResult) -> bool:
    existing_failed = (
        session.query(DetailJob)
        .filter(
            DetailJob.info_id == job.info_id,
            DetailJob.status == "failed",
            DetailJob.id != job.id,
        )
        .order_by(DetailJob.updated_at.desc(), DetailJob.id.desc())
        .first()
    )
    if not existing_failed:
        return False

    existing_failed.channel_code = job.channel_code or existing_failed.channel_code
    existing_failed.attempt_count = max(existing_failed.attempt_count or 0, job.attempt_count or 0)
    existing_failed.max_attempts = max(existing_failed.max_attempts or 0, job.max_attempts or 0)
    existing_failed.last_failure_reason = result.failure_reason or "detail_unavailable"
    existing_failed.strategy_hint = job.strategy_hint or existing_failed.strategy_hint
    existing_failed.next_run_at = job.next_run_at
    existing_failed.updated_at = datetime.now()
    job.status = f"merged_{job.id}"
    job.last_failure_reason = "merged_into_existing_failed_job"
    job.updated_at = datetime.now()
    return True


def _apply_failure(session, job: DetailJob, result: DetailPipelineResult):
    job.last_failure_reason = result.failure_reason or "detail_unavailable"
    if job.attempt_count >= job.max_attempts:
        if _merge_into_existing_failed_job(session, job, result):
            return
        job.status = "failed"
        return
    job.status = "pending"
    job.next_run_at = datetime.now() + _retry_delay(job.attempt_count)


def _run_detail_runner(runner: DetailRunner, info: Info, job: DetailJob) -> DetailPipelineResult:
    if runner is crawler_detail_runner:
        return runner(info, strategy_hint=job.strategy_hint or "")
    return runner(info)


def _recover_stale_running_jobs(session, now: datetime) -> int:
    timeout_before = now - timedelta(minutes=DETAIL_JOB_RUNNING_TIMEOUT_MINUTES)
    stale_jobs = (
        session.query(DetailJob)
        .filter(
            DetailJob.status == "running",
            (DetailJob.updated_at.is_(None)) | (DetailJob.updated_at <= timeout_before),
        )
        .all()
    )
    for job in stale_jobs:
        job.status = "pending"
        job.next_run_at = now
        job.last_failure_reason = "running_timeout_recovered"
        job.updated_at = now
    return len(stale_jobs)


def _claim_pending_detail_jobs(session, limit: int, now: datetime) -> list[int]:
    _recover_stale_running_jobs(session, now)
    session.flush()
    jobs = (
        session.query(DetailJob.id)
        .filter(DetailJob.status == "pending", DetailJob.next_run_at <= now)
        .order_by(DetailJob.priority.desc(), DetailJob.next_run_at.asc(), DetailJob.id.asc())
        .limit(limit)
        .all()
    )
    claimed_ids = []
    for row in jobs:
        job_id = row[0]
        updated_count = (
            session.query(DetailJob)
            .filter(DetailJob.id == job_id, DetailJob.status == "pending")
            .update(
                {
                    DetailJob.status: "running",
                    DetailJob.attempt_count: func.coalesce(DetailJob.attempt_count, 0) + 1,
                    DetailJob.updated_at: now,
                },
                synchronize_session=False,
            )
        )
        if updated_count:
            claimed_ids.append(job_id)
    session.commit()
    return claimed_ids


def process_pending_detail_jobs(session, runner: DetailRunner, limit: int = 20) -> dict:
    """执行待补偿详情任务，并更新任务状态、Info 详情字段和采集日志。"""

    job_ids = _claim_pending_detail_jobs(session, limit, datetime.now())
    succeeded_count = 0
    failed_count = 0
    xhs_consecutive_count = 0

    for job_id in job_ids:
        job = session.get(DetailJob, job_id)
        if not job or job.status != "running":
            continue
        info = session.get(Info, job.info_id)
        if not info:
            job.status = "cancelled"
            job.last_failure_reason = "info_not_found"
            job.updated_at = datetime.now()
            session.commit()
            continue

        result = _run_detail_runner(runner, info, job)

        if _is_usable_detail_result(result, job.strategy_hint or ""):
            _apply_success(info, job, result)
            mark_event_analysis_stale_for_info(session, info.id)
            succeeded_count += 1
        else:
            _apply_failure(session, job, result)
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

        # Rate-limit: add longer delay for xiaohongshu to avoid rendering failures
        if job.channel_code == "xiaohongshu":
            xhs_consecutive_count += 1
            delay = random.uniform(3.0, 6.0) if xhs_consecutive_count % 3 == 0 else random.uniform(1.5, 3.0)
            time.sleep(delay)
        else:
            xhs_consecutive_count = 0
            time.sleep(random.uniform(0.3, 1.0))
    return {"succeeded_count": succeeded_count, "failed_count": failed_count}

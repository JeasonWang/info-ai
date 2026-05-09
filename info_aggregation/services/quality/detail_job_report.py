from collections import Counter

from database import DetailJob, Info


def _job_sample(job: DetailJob) -> dict:
    info = job.info
    return {
        "id": job.id,
        "info_id": job.info_id,
        "title": info.title if info else "",
        "channel_code": job.channel_code,
        "status": job.status,
        "priority": job.priority,
        "strategy_hint": job.strategy_hint,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "last_failure_reason": job.last_failure_reason,
        "next_run_at": job.next_run_at.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_at else None,
        "detail_score": info.detail_score if info else 0,
        "detail_fetch_status": info.detail_fetch_status if info else "",
    }


def build_detail_job_report(
    session,
    sample_limit: int = 10,
    channel_code: str = "",
    failure_reason: str = "",
) -> dict:
    """生成详情补偿队列报告，供管理后台观察积压和失败原因。"""

    query = session.query(DetailJob).join(Info, Info.id == DetailJob.info_id)
    if channel_code:
        query = query.filter(DetailJob.channel_code == channel_code)
    if failure_reason:
        query = query.filter(DetailJob.last_failure_reason == failure_reason)
    jobs = query.order_by(DetailJob.id.desc()).all()
    status_counts = Counter(job.status for job in jobs)
    channel_counts = Counter(job.channel_code for job in jobs if job.channel_code)
    failure_counts = Counter(job.last_failure_reason for job in jobs if job.last_failure_reason)
    strategy_counts = Counter(job.strategy_hint or "auto" for job in jobs)

    pending_jobs = sorted(
        [job for job in jobs if job.status == "pending"],
        key=lambda item: (-item.priority, item.next_run_at or item.created_at, item.id),
    )[:sample_limit]
    failed_jobs = sorted(
        [job for job in jobs if job.status == "failed"],
        key=lambda item: (item.updated_at or item.created_at, item.id),
        reverse=True,
    )[:sample_limit]

    return {
        "total": len(jobs),
        "status_counts": dict(sorted(status_counts.items())),
        "channel_counts": dict(sorted(channel_counts.items())),
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "top_failure_reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(failure_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        ],
        "pending_samples": [_job_sample(job) for job in pending_jobs],
        "failed_samples": [_job_sample(job) for job in failed_jobs],
    }

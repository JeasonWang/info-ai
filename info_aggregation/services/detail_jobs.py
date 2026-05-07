from datetime import datetime

from database import DetailJob, Info


OPEN_DETAIL_JOB_STATUSES = {"pending", "running"}


def _needs_detail_job(info: Info) -> bool:
    status = (info.detail_fetch_status or "").strip()
    if status in {"pending", "failed", "list_only"}:
        return True
    if status == "partial" and (info.detail_score or 0) < 60:
        return True
    return (info.detail_score or 0) < 60 or (info.detail_content_length or len(info.content or "")) < 30


def _failure_reason(info: Info) -> str:
    if info.detail_fetch_error:
        return info.detail_fetch_error[:255]
    if (info.detail_score or 0) < 60:
        return "low_detail_score"
    if (info.detail_content_length or len(info.content or "")) < 30:
        return "short_detail_content"
    return "detail_incomplete"


def enqueue_low_quality_detail_jobs(session, limit: int = 100) -> dict:
    """把低分或失败详情内容放入补偿队列，避免同一内容重复创建开放任务。"""

    created_count = 0
    skipped_count = 0
    candidates = (
        session.query(Info)
        .filter(Info.is_deleted == 0)
        .order_by(Info.updated_at.desc(), Info.id.desc())
        .limit(limit)
        .all()
    )

    for info in candidates:
        if not _needs_detail_job(info):
            continue
        existing = (
            session.query(DetailJob)
            .filter(DetailJob.info_id == info.id, DetailJob.status.in_(OPEN_DETAIL_JOB_STATUSES))
            .first()
        )
        if existing:
            skipped_count += 1
            continue
        session.add(
            DetailJob(
                info_id=info.id,
                channel_code=info.channel.code if info.channel else "",
                status="pending",
                priority=80 if (info.detail_score or 0) < 60 else 50,
                attempt_count=0,
                max_attempts=3,
                next_run_at=datetime.now(),
                last_failure_reason=_failure_reason(info),
                strategy_hint="auto",
            )
        )
        created_count += 1

    session.commit()
    return {"created_count": created_count, "skipped_count": skipped_count}

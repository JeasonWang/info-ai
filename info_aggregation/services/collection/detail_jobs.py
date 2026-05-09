from datetime import datetime

from database import DetailJob, Info
from services.acquisition_quality import build_acquisition_quality_profile


OPEN_DETAIL_JOB_STATUSES = {"pending", "running"}
REUSABLE_DETAIL_JOB_STATUSES = {"failed", "cancelled"}


def _needs_detail_job(info: Info) -> bool:
    return build_acquisition_quality_profile(info).should_enqueue_detail_job


def _failure_reason(info: Info) -> str:
    if info.detail_fetch_error:
        return info.detail_fetch_error[:255]
    profile = build_acquisition_quality_profile(info)
    if profile.risk_reasons:
        return profile.risk_reasons[0][:255]
    return profile.recommended_action[:255]


def _job_priority(info: Info) -> int:
    profile = build_acquisition_quality_profile(info)
    return profile.attention_priority or (80 if (info.detail_score or 0) < 60 else 50)


def _strategy_hint(info: Info) -> str:
    return build_acquisition_quality_profile(info).recommended_action


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
        existing_open = (
            session.query(DetailJob)
            .filter(DetailJob.info_id == info.id, DetailJob.status.in_(OPEN_DETAIL_JOB_STATUSES))
            .first()
        )
        if existing_open:
            skipped_count += 1
            continue

        reusable = (
            session.query(DetailJob)
            .filter(DetailJob.info_id == info.id, DetailJob.status.in_(REUSABLE_DETAIL_JOB_STATUSES))
            .order_by(DetailJob.updated_at.desc(), DetailJob.id.desc())
            .first()
        )
        if reusable:
            reusable.status = "pending"
            reusable.channel_code = info.channel.code if info.channel else reusable.channel_code
            reusable.priority = _job_priority(info)
            reusable.attempt_count = 0
            reusable.max_attempts = 3
            reusable.next_run_at = datetime.now()
            reusable.last_failure_reason = _failure_reason(info)
            reusable.strategy_hint = _strategy_hint(info)
            created_count += 1
            continue

        session.add(
            DetailJob(
                info_id=info.id,
                channel_code=info.channel.code if info.channel else "",
                status="pending",
                priority=_job_priority(info),
                attempt_count=0,
                max_attempts=3,
                next_run_at=datetime.now(),
                last_failure_reason=_failure_reason(info),
                strategy_hint=_strategy_hint(info),
            )
        )
        created_count += 1

    session.commit()
    return {"created_count": created_count, "skipped_count": skipped_count}

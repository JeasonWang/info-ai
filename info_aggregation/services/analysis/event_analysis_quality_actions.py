from datetime import datetime

from database import DetailJob, Event, EventAnalysisRun, EventItemLink, Info
from services.acquisition_quality import build_acquisition_quality_profile
from services.detail_jobs import OPEN_DETAIL_JOB_STATUSES, REUSABLE_DETAIL_JOB_STATUSES


def _latest_runs_by_event(session) -> dict[int, EventAnalysisRun]:
    rows = (
        session.query(EventAnalysisRun)
        .order_by(EventAnalysisRun.event_id.asc(), EventAnalysisRun.created_at.desc(), EventAnalysisRun.id.desc())
        .all()
    )
    latest: dict[int, EventAnalysisRun] = {}
    for row in rows:
        latest.setdefault(row.event_id, row)
    return latest


def _risk_event_ids(session, limit: int) -> list[int]:
    events = session.query(Event).filter(Event.status == "active").order_by(Event.last_updated_at.desc()).all()
    latest_runs = _latest_runs_by_event(session)
    scored: list[tuple[float, int]] = []
    for event in events:
        run = latest_runs.get(event.id)
        if run is None:
            scored.append((100.0, event.id))
            continue
        score = 0.0
        score += max(0.0, 60.0 - float(run.quality_score or 0))
        score += max(0.0, 0.6 - float(run.confidence or 0)) * 100
        score += 15.0 if run.fallback_used or run.status == "fallback" else 0.0
        if score > 0:
            scored.append((score, event.id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [event_id for _, event_id in scored[:limit]]


def _linked_weak_infos(session, event_ids: list[int]) -> list[tuple[int, Info]]:
    if not event_ids:
        return []
    rows = (
        session.query(EventItemLink.event_id, Info)
        .join(Info, Info.id == EventItemLink.item_id)
        .filter(EventItemLink.event_id.in_(event_ids), Info.is_deleted == 0)
        .all()
    )
    selected: list[tuple[int, Info]] = []
    for event_id, info in rows:
        profile = build_acquisition_quality_profile(info)
        if profile.should_enqueue_detail_job:
            selected.append((event_id, info))
    selected.sort(
        key=lambda row: (
            -build_acquisition_quality_profile(row[1]).attention_priority,
            build_acquisition_quality_profile(row[1]).completeness_score,
            row[1].id,
        )
    )
    return selected


def _failure_reason(info: Info) -> str:
    if info.detail_fetch_error:
        return info.detail_fetch_error[:255]
    profile = build_acquisition_quality_profile(info)
    if profile.risk_reasons:
        return profile.risk_reasons[0][:255]
    return "event_analysis_quality_low"


def _priority(info: Info) -> int:
    profile = build_acquisition_quality_profile(info)
    return max(profile.attention_priority or 80, 90)


def _strategy_hint(info: Info) -> str:
    return build_acquisition_quality_profile(info).recommended_action or "retry_full_article_detail"


def enqueue_event_analysis_detail_jobs(session, limit: int = 20) -> dict:
    """把事件分析风险事件中的弱来源放入详情补偿队列。"""

    limit = max(1, min(limit, 100))
    risk_event_ids = _risk_event_ids(session, limit=limit)
    weak_infos = _linked_weak_infos(session, risk_event_ids)[:limit]
    created_count = 0
    skipped_count = 0
    selected_samples: list[dict] = []

    for event_id, info in weak_infos:
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
            job = reusable
            job.status = "pending"
            job.attempt_count = 0
            job.max_attempts = 3
            job.next_run_at = datetime.now()
        else:
            job = DetailJob(info_id=info.id, status="pending", attempt_count=0, max_attempts=3, next_run_at=datetime.now())
            session.add(job)

        job.channel_code = info.channel.code if info.channel else job.channel_code
        job.priority = _priority(info)
        job.last_failure_reason = _failure_reason(info)
        job.strategy_hint = _strategy_hint(info)
        created_count += 1
        profile = build_acquisition_quality_profile(info)
        selected_samples.append(
            {
                "event_id": event_id,
                "info_id": info.id,
                "title": info.title,
                "channel_code": info.channel.code if info.channel else "",
                "quality_level": profile.quality_level,
                "attention_priority": profile.attention_priority,
                "recommended_action": profile.recommended_action,
                "quality_summary": profile.summary,
            }
        )

    session.commit()
    return {
        "created_count": created_count,
        "skipped_count": skipped_count,
        "risk_event_count": len(risk_event_ids),
        "selected_count": len(selected_samples),
        "selected_samples": selected_samples,
    }

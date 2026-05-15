from datetime import datetime

from database import DetailJob, Event, EventAnalysisRun, EventItemLink, Info
from services.analysis.event_analysis_reanalysis import rebuild_stale_event_analysis
from services.analysis.event_display_quality import backfill_event_display_quality, link_secondary_fact_sources_for_social_events
from services.collection.acquisition_quality import build_acquisition_quality_profile
from services.collection.detail_job_worker import crawler_detail_runner, process_pending_detail_jobs
from services.collection.detail_jobs import OPEN_DETAIL_JOB_STATUSES, REUSABLE_DETAIL_JOB_STATUSES


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
    linked_infos = _linked_infos_by_event(session, [event.id for event in events])
    scored: list[tuple[float, int]] = []
    for event in events:
        run = latest_runs.get(event.id)
        infos = linked_infos.get(event.id, [])
        weak_count = _weak_source_count(infos)
        source_quality_risk = _source_quality_is_actionable(infos, weak_count)
        if run is None:
            scored.append((100.0, event.id))
            continue
        score = 0.0
        score += max(0.0, 60.0 - float(run.quality_score or 0))
        score += max(0.0, 0.6 - float(run.confidence or 0)) * 100
        score += 15.0 if run.fallback_used or run.status == "fallback" else 0.0
        if source_quality_risk:
            score += min(30.0, weak_count * 12.0)
        if score > 0:
            scored.append((score, event.id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [event_id for _, event_id in scored[:limit]]


def _linked_infos_by_event(session, event_ids: list[int]) -> dict[int, list[Info]]:
    if not event_ids:
        return {}
    rows = (
        session.query(EventItemLink.event_id, Info)
        .join(Info, Info.id == EventItemLink.item_id)
        .filter(EventItemLink.event_id.in_(event_ids), Info.is_deleted == 0)
        .all()
    )
    grouped: dict[int, list[Info]] = {event_id: [] for event_id in event_ids}
    for event_id, info in rows:
        grouped.setdefault(event_id, []).append(info)
    return grouped


def _weak_source_count(infos: list[Info]) -> int:
    return sum(1 for info in infos if build_acquisition_quality_profile(info).needs_attention)


def _source_quality_is_actionable(infos: list[Info], weak_count: int) -> bool:
    if weak_count <= 0:
        return False
    source_count = len({info.id for info in infos if info.id}) or len(infos)
    usable_count = 0
    complete_count = 0
    for info in infos:
        profile = build_acquisition_quality_profile(info)
        if profile.usable or ((info.detail_fetch_status or "") in {"complete", "partial"} and (info.detail_score or 0) >= 60):
            usable_count += 1
        if profile.status == "complete" or ((info.detail_fetch_status or "") == "complete" and (info.detail_score or 0) >= 70):
            complete_count += 1
    weak_ratio = weak_count / max(source_count, 1)
    if complete_count == 0 or usable_count == 0:
        return True
    return weak_count >= 2 and weak_ratio >= 0.5


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


def prioritize_source_quality_governance(session, limit: int = 20, runner=None) -> dict:
    """一键治理当前来源质量风险：定向入队、执行补偿、补事实源、重分析和刷新展示质量。"""

    limit = max(1, min(limit, 100))
    enqueue_result = enqueue_event_analysis_detail_jobs(session, limit=limit)
    process_result = process_pending_detail_jobs(session, runner=runner or crawler_detail_runner, limit=limit)
    fact_source_result = link_secondary_fact_sources_for_social_events(session, limit=limit * 3)
    should_reanalyze = (
        process_result.get("succeeded_count", 0) > 0
        or fact_source_result.get("linked_count", 0) > 0
        or enqueue_result.get("created_count", 0) > 0
    )
    reanalyze_result = (
        rebuild_stale_event_analysis(session, limit=max(200, limit * 10))
        if should_reanalyze
        else {"stale_count": 0, "rebuilt": False, "event_count": 0}
    )
    display_result = backfill_event_display_quality(session, limit=max(200, limit * 10))
    return {
        "limit": limit,
        "enqueue": enqueue_result,
        "process": process_result,
        "fact_source": fact_source_result,
        "reanalyze": reanalyze_result,
        "display_quality": display_result,
    }

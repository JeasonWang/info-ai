from datetime import datetime

from database import Event, EventAnalysisRun, EventItemLink, Info
from services.collection.acquisition_quality import build_acquisition_quality_profile


def mark_event_analysis_stale_for_info(session, info_id: int, reason: str = "detail_compensation_succeeded") -> int:
    """详情补偿更新正文后，将关联事件最新分析标记为过期。"""

    event_ids = [
        row[0]
        for row in session.query(EventItemLink.event_id)
        .filter(EventItemLink.item_id == info_id)
        .distinct()
        .all()
    ]
    marked_count = 0
    for event_id in event_ids:
        latest_run = (
            session.query(EventAnalysisRun)
            .filter(EventAnalysisRun.event_id == event_id)
            .order_by(EventAnalysisRun.created_at.desc(), EventAnalysisRun.id.desc())
            .first()
        )
        if not latest_run or latest_run.status == "stale":
            continue
        latest_run.status = "stale"
        latest_run.failure_reason = reason
        latest_run.finished_at = datetime.now()
        marked_count += 1
    return marked_count


def rebuild_stale_event_analysis(session, limit: int = 200) -> dict:
    """存在过期分析时触发事件重建，让补偿后的正文重新进入事件分析。"""

    stale_count = session.query(EventAnalysisRun).filter(EventAnalysisRun.status == "stale").count()
    if stale_count <= 0:
        return {"stale_count": 0, "rebuilt": False, "event_count": 0}

    from services.analysis.event_builder import _reanalyze_existing_event, rebuild_events
    from database import Event

    stale_runs = (
        session.query(EventAnalysisRun)
        .filter(EventAnalysisRun.status == "stale")
        .order_by(EventAnalysisRun.created_at.desc(), EventAnalysisRun.id.desc())
        .limit(limit)
        .all()
    )
    rebuilt_event_ids: set[int] = set()
    for run in stale_runs:
        if run.event_id in rebuilt_event_ids:
            continue
        event = session.get(Event, run.event_id)
        if not event:
            continue
        if _reanalyze_existing_event(session, event):
            rebuilt_event_ids.add(event.id)

    if not rebuilt_event_ids:
        rebuild_events(session, limit=limit)
    stale_ids = [run.id for run in stale_runs]
    if stale_ids:
        session.query(EventAnalysisRun).filter(EventAnalysisRun.id.in_(stale_ids)).update(
            {EventAnalysisRun.status: "superseded"},
            synchronize_session=False,
        )
    session.commit()
    event_count = session.query(Event).filter(Event.status == "active").count()
    return {"stale_count": stale_count, "rebuilt": True, "event_count": event_count}


def mark_low_confidence_complete_events_stale(session, limit: int = 100) -> dict:
    """把低置信但来源已完整可用的事件标记为过期，供重分析应用新规则。"""

    limit = max(1, min(limit, 1000))
    latest_runs = (
        session.query(EventAnalysisRun)
        .join(Event, Event.id == EventAnalysisRun.event_id)
        .filter(Event.status == "active")
        .filter(EventAnalysisRun.status.in_(("succeeded", "fallback")))
        .filter((EventAnalysisRun.confidence < 0.6) | (EventAnalysisRun.quality_score < 60))
        .order_by(EventAnalysisRun.created_at.desc(), EventAnalysisRun.id.desc())
        .all()
    )
    seen_event_ids: set[int] = set()
    candidates: list[EventAnalysisRun] = []
    for run in latest_runs:
        if run.event_id in seen_event_ids:
            continue
        seen_event_ids.add(run.event_id)
        if _event_has_complete_reanalysis_sources(session, run.event_id):
            candidates.append(run)
        if len(candidates) >= limit:
            break

    now = datetime.now()
    for run in candidates:
        run.status = "stale"
        run.failure_reason = "low_confidence_complete_source_reanalysis"
        run.finished_at = now

    session.commit()
    return {
        "candidate_count": len(candidates),
        "marked_count": len(candidates),
        "reason": "low_confidence_complete_source_reanalysis",
        "event_ids": [run.event_id for run in candidates],
    }


def _event_has_complete_reanalysis_sources(session, event_id: int) -> bool:
    infos = (
        session.query(Info)
        .join(EventItemLink, EventItemLink.item_id == Info.id)
        .filter(EventItemLink.event_id == event_id, Info.is_deleted == 0)
        .all()
    )
    if not infos:
        return False
    profiles = [build_acquisition_quality_profile(info) for info in infos]
    source_count = len(profiles)
    usable_complete = [
        profile
        for profile in profiles
        if profile.usable and profile.status == "complete" and profile.completeness_score >= 80
    ]
    weak_count = sum(1 for profile in profiles if profile.needs_attention)
    if bool(usable_complete) and weak_count == 0:
        return True
    return (
        source_count == 2
        and weak_count == 1
        and len(usable_complete) == 1
    )

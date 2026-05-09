from datetime import datetime

from database import EventAnalysisRun, EventItemLink


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

    from services.event_builder import rebuild_events
    from database import Event

    rebuild_events(session, limit=limit)
    event_count = session.query(Event).filter(Event.status == "active").count()
    return {"stale_count": stale_count, "rebuilt": True, "event_count": event_count}

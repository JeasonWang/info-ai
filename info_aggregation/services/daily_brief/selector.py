"""Select top N events for daily brief generation."""
import logging

from sqlalchemy import desc

from database import get_session, Event, EventAnalysisRun, EventTimelineEntry

logger = logging.getLogger(__name__)

_QUALITY_LEVELS = ("excellent", "good")


def select_top_events(top_n: int = 5) -> list[dict]:
    """
    Select top N events for daily brief.

    Criteria: display_quality_level in ("excellent", "good"), status="active"
    Ordered by composite_score DESC.
    Returns list of dicts with event info + latest analysis results.
    """
    with get_session() as session:
        events = (
            session.query(Event)
            .filter(
                Event.display_quality_level.in_(_QUALITY_LEVELS),
                Event.status == "active",
            )
            .order_by(desc(Event.composite_score))
            .limit(top_n)
            .all()
        )

        result = []
        for event in events:
            latest_run = (
                session.query(EventAnalysisRun)
                .filter(
                    EventAnalysisRun.event_id == event.id,
                    EventAnalysisRun.status == "succeeded",
                )
                .order_by(desc(EventAnalysisRun.created_at))
                .first()
            )

            timeline_entries = (
                session.query(EventTimelineEntry)
                .filter(EventTimelineEntry.event_id == event.id)
                .order_by(EventTimelineEntry.occurred_at.asc())
                .limit(3)
                .all()
            )

            timeline_highlights = [
                {
                    "occurred_at": entry.occurred_at.isoformat() if entry.occurred_at else None,
                    "summary": entry.summary,
                }
                for entry in timeline_entries
            ]

            category_code = ""
            if event.category:
                category_code = event.category.code or ""

            result.append({
                "id": event.id,
                "title": event.title,
                "composite_score": event.composite_score,
                "one_line_summary": event.one_line_summary or "",
                "what_happened": getattr(latest_run, "_what_happened", "") or "",
                "why_it_matters": getattr(latest_run, "_why_it_matters", "") or "",
                "timeline_highlights": timeline_highlights,
                "event_time": event.last_updated_at.isoformat() if event.last_updated_at else None,
                "source_count": event.source_count or 0,
                "category_code": category_code,
            })

        return result


def get_event_summaries_for_brief(events: list[dict]) -> str:
    """Build a text block summarizing events for LLM prompt."""
    parts = []
    for idx, ev in enumerate(events, 1):
        lines = [
            f"事件{idx}: {ev['title']}",
            f"综合得分: {ev['composite_score']}",
            f"一句话摘要: {ev['one_line_summary']}",
            f"来源数: {ev['source_count']}",
        ]
        if ev.get("timeline_highlights"):
            for th in ev["timeline_highlights"][:3]:
                lines.append(f"  - {th.get('occurred_at', '')[:10]} {th.get('summary', '')}")
        parts.append(chr(10).join(lines))
    return (chr(10) + chr(10)).join(parts)
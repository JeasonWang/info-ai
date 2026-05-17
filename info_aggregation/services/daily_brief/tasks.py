"""Daily brief scheduled task."""
import logging
from datetime import date

from database import get_session, DailyBrief
from services.analysis.system_config import get_config_int
from .selector import select_top_events
from .generator import generate_brief_content
from .renderer import render_markdown, render_html, render_text

logger = logging.getLogger(__name__)


def generate_daily_brief():
    """
    Main entry point for daily brief generation.
    Called by APScheduler.
    """
    today = date.today()
    top_n = get_config_int("daily_brief_top_n", 5)

    logger.info("开始生成每日简报, date=%s, top_n=%d", today, top_n)

    # Check if already generated today
    with get_session() as session:
        existing = (
            session.query(DailyBrief)
            .filter(DailyBrief.brief_date == today)
            .first()
        )
        if existing is not None:
            logger.info("今日简报已存在, id=%d, status=%s", existing.id, existing.status)
            return existing

    # Select top events
    events = select_top_events(top_n=top_n)
    if not events:
        logger.warning("没有符合条件的优质事件，跳过简报生成")
        return None

    # Generate brief content via LLM
    brief_content = generate_brief_content(events)

    # Render to multiple formats
    brief_data = {
        "headline": brief_content["headline"],
        "events": brief_content["events"],
    }
    content_md = render_markdown(brief_data)
    content_html = render_html(brief_data)
    content_text = render_text(brief_data)

    # Save to database
    event_ids = [ev["id"] for ev in events]
    record = DailyBrief(
        brief_date=today,
        headline=brief_content["headline"],
        content_md=content_md,
        content_html=content_html,
        content_text=content_text,
        event_ids=event_ids,
        event_count=len(events),
        status="draft",
        model_name=brief_content.get("model_name", ""),
        llm_config_id=brief_content.get("llm_config_id"),
    )

    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        logger.info(
            "每日简报生成完成, id=%d, events=%d, model=%s",
            record.id,
            record.event_count,
            record.model_name,
        )
        return record


def get_daily_briefs(limit: int = 30) -> list[dict]:
    """Get recent daily briefs ordered by date DESC."""
    with get_session() as session:
        briefs = (
            session.query(DailyBrief)
            .order_by(DailyBrief.brief_date.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": b.id,
                "brief_date": b.brief_date.isoformat() if b.brief_date else None,
                "headline": b.headline,
                "event_count": b.event_count,
                "status": b.status,
                "model_name": b.model_name,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in briefs
        ]


def get_daily_brief_by_date(brief_date: date) -> dict | None:
    """Get a daily brief by date, returns full content."""
    with get_session() as session:
        brief = (
            session.query(DailyBrief)
            .filter(DailyBrief.brief_date == brief_date)
            .first()
        )
        if brief is None:
            return None
        return {
            "id": brief.id,
            "brief_date": brief.brief_date.isoformat() if brief.brief_date else None,
            "headline": brief.headline,
            "content_md": brief.content_md,
            "content_html": brief.content_html,
            "content_text": brief.content_text,
            "event_ids": brief.event_ids,
            "event_count": brief.event_count,
            "status": brief.status,
            "model_name": brief.model_name,
            "created_at": brief.created_at.isoformat() if brief.created_at else None,
        }
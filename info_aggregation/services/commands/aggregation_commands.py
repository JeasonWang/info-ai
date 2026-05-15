"""Redis command handlers for the aggregation worker."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from cleaners import clean_info_list
from crawlers.registry import crawler_registry
from database import Channel, Event, Info, get_session
from scheduler import (
    _fetch_details_for_items,
    _record_crawl_run,
    _save_crawled_data,
    _sync_crawl_tasks,
)
from services import (
    archive_duplicate_title_infos,
    archive_low_quality_infos,
    enqueue_event_analysis_detail_jobs,
    mark_low_confidence_complete_events_stale,
    prioritize_source_quality_governance,
    rebuild_events,
    rebuild_stale_event_analysis,
    refresh_info_semantics,
)
from services.collection.acquisition_quality import build_acquisition_quality_profile
from services.collection.credential_provider import CredentialProvider
from services.quality.data_quality_report import save_data_quality_snapshot

logger = logging.getLogger(__name__)


class AggregationCommandHandler:
    """Execute commands that info-serve submits through Redis."""

    def handle(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        handlers = {
            "trigger_crawl": self.trigger_crawl,
            "rebuild_events": self.rebuild_events,
            "refresh_quality": self.refresh_quality,
            "retry_low_quality_details": self.retry_low_quality_details,
            "enqueue_event_analysis_detail_jobs": self.enqueue_event_analysis_detail_jobs,
            "prioritize_source_quality_governance": self.prioritize_source_quality_governance,
            "mark_low_confidence_event_analysis_stale": self.mark_low_confidence_event_analysis_stale,
            "rebuild_stale_event_analysis": self.rebuild_stale_event_analysis,
            "archive_low_quality": self.archive_low_quality,
            "archive_duplicate_titles": self.archive_duplicate_titles,
            "test_channel_credentials": self.test_channel_credentials,
            "invalidate_credentials": self.invalidate_credentials,
        }
        handler = handlers.get(action)
        if handler is None:
            raise ValueError(f"unsupported aggregation command action: {action}")
        logger.info("执行聚合命令 action=%s payload_keys=%s", action, sorted(payload.keys()))
        return handler(payload)

    def trigger_crawl(self, payload: dict[str, Any]) -> dict[str, Any]:
        channel_code = str(payload.get("channel_code") or "").strip()
        if not channel_code:
            raise ValueError("channel_code is required")
        return _run_manual_crawl(channel_code)

    def rebuild_events(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = get_session()
        try:
            limit = _optional_positive_int(payload.get("limit"))
            if limit:
                rebuild_events(session, limit=limit)
            else:
                rebuild_events(session)
            event_count = session.query(Event).count()
            return {"event_count": event_count}
        finally:
            session.close()

    def refresh_quality(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = get_session()
        try:
            semantic_result = refresh_info_semantics(session)
            rebuild_events(session)
            snapshot = save_data_quality_snapshot(session)
            event_count = session.query(Event).count()
            return {
                **semantic_result,
                "quality_snapshot_id": snapshot.id,
                "event_count": event_count,
            }
        finally:
            session.close()

    def retry_low_quality_details(self, payload: dict[str, Any]) -> dict[str, Any]:
        limit = _bounded_int(payload.get("limit"), default=20, minimum=1, maximum=50)
        session = get_session()
        try:
            candidates = (
                session.query(Info)
                .join(Channel, Channel.id == Info.channel_id)
                .filter(Info.is_deleted == 0)
                .order_by(Info.updated_at.desc(), Info.id.desc())
                .limit(limit * 5)
                .all()
            )
            selected = []
            for info in candidates:
                profile = build_acquisition_quality_profile(info)
                if profile.should_enqueue_detail_job:
                    selected.append((info, profile))
            selected.sort(key=lambda item: (-item[1].attention_priority, item[1].completeness_score, item[0].id))
            selected = selected[:limit]
            infos = [info for info, _ in selected]
            selected_samples = [
                {
                    "info_id": info.id,
                    "title": info.title,
                    "channel_code": info.channel.code if info.channel else "",
                    "attention_priority": profile.attention_priority,
                    "quality_level": profile.quality_level,
                    "risk_reasons": profile.risk_reasons,
                    "recommended_action": profile.recommended_action,
                    "quality_summary": profile.summary,
                }
                for info, profile in selected
            ]
            grouped_ids: dict[str, list[int]] = {}
            for info in infos:
                channel_code = info.channel.code if info.channel else ""
                if channel_code:
                    grouped_ids.setdefault(channel_code, []).append(info.id)
        finally:
            session.close()

        total_success = 0
        total_failed = 0
        channel_results = {}
        for channel_code, ids in grouped_ids.items():
            result = _fetch_details_for_items(channel_code, ids)
            success_count = int(result.get("detail_success_count", 0))
            failed_count = int(result.get("detail_failed_count", 0))
            total_success += success_count
            total_failed += failed_count
            channel_results[channel_code] = {
                "info_ids": ids,
                "detail_success_count": success_count,
                "detail_failed_count": failed_count,
            }

        session = get_session()
        try:
            semantic_result = refresh_info_semantics(session)
            rebuild_events(session)
            snapshot = save_data_quality_snapshot(session)
            event_count = session.query(Event).count()
            return {
                "selected_count": len(infos),
                "selected_samples": selected_samples,
                "detail_success_count": total_success,
                "detail_failed_count": total_failed,
                "channel_results": channel_results,
                "semantic_updated_count": semantic_result.get("updated_count", semantic_result.get("changed_count", 0)),
                "quality_snapshot_id": snapshot.id,
                "event_count": event_count,
            }
        finally:
            session.close()

    def enqueue_event_analysis_detail_jobs(self, payload: dict[str, Any]) -> dict[str, Any]:
        limit = _bounded_int(payload.get("limit"), default=20, minimum=1, maximum=100)
        session = get_session()
        try:
            return enqueue_event_analysis_detail_jobs(session, limit=limit)
        finally:
            session.close()

    def prioritize_source_quality_governance(self, payload: dict[str, Any]) -> dict[str, Any]:
        limit = _bounded_int(payload.get("limit"), default=20, minimum=1, maximum=100)
        session = get_session()
        try:
            return prioritize_source_quality_governance(session, limit=limit)
        finally:
            session.close()

    def rebuild_stale_event_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        limit = _bounded_int(payload.get("limit"), default=200, minimum=1, maximum=1000)
        session = get_session()
        try:
            return rebuild_stale_event_analysis(session, limit=limit)
        finally:
            session.close()

    def mark_low_confidence_event_analysis_stale(self, payload: dict[str, Any]) -> dict[str, Any]:
        limit = _bounded_int(payload.get("limit"), default=100, minimum=1, maximum=1000)
        session = get_session()
        try:
            return mark_low_confidence_complete_events_stale(session, limit=limit)
        finally:
            session.close()

    def archive_low_quality(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = get_session()
        try:
            archive_result = archive_low_quality_infos(session)
            rebuild_events(session)
            return {
                **archive_result,
                "event_count": session.query(Event).count(),
            }
        finally:
            session.close()

    def archive_duplicate_titles(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = get_session()
        try:
            archive_result = archive_duplicate_title_infos(session)
            rebuild_events(session)
            return {
                **archive_result,
                "event_count": session.query(Event).count(),
            }
        finally:
            session.close()

    def test_channel_credentials(self, payload: dict[str, Any]) -> dict[str, Any]:
        channel_code = str(payload.get("channel_code") or "").strip()
        if not channel_code:
            raise ValueError("channel_code is required")
        if channel_code not in {"weibo", "zhihu", "xiaohongshu"}:
            raise ValueError(f"unsupported credential test channel: {channel_code}")
        provider = CredentialProvider.get_instance(session_factory=get_session)
        result = provider.verify_credential(channel_code)
        return {
            "channel_code": channel_code,
            "success": bool(result.get("success")),
            "response_code": int(result.get("response_code") or 0),
            "message": result.get("message", ""),
        }

    def invalidate_credentials(self, payload: dict[str, Any]) -> dict[str, Any]:
        channel_code = str(payload.get("channel_code") or "").strip()
        CredentialProvider.invalidate_cache()
        return {"channel_code": channel_code, "cache_invalidated": True}


def handle_aggregation_command(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return AggregationCommandHandler().handle(action, payload)


def _run_manual_crawl(channel_code: str) -> dict[str, Any]:
    started_at = datetime.now()
    raw_count = 0
    cleaned_count = 0
    saved_count = 0
    detail_result = {"detail_success_count": 0, "detail_failed_count": 0}
    status = "success"
    error_message = ""

    try:
        crawler = crawler_registry.get(channel_code)
        if not crawler:
            raise ValueError(f"channel {channel_code} is not registered")

        with crawler_registry.get_lock(channel_code):
            raw_items = crawler.safe_crawl()
        raw_count = len(raw_items)
        cleaned_items = clean_info_list(raw_items)
        cleaned_count = len(cleaned_items)
        saved_ids = _save_crawled_data(channel_code, cleaned_items)
        saved_count = len(saved_ids)
        detail_result = _fetch_details_for_items(channel_code, saved_ids)
        if detail_result["detail_failed_count"] > 0:
            status = "partial"
    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        logger.error("手动采集命令失败 channel=%s error=%s", channel_code, exc, exc_info=True)
        raise
    finally:
        session = get_session()
        try:
            _sync_crawl_tasks(session)
            _record_crawl_run(
                session,
                channel_code=channel_code,
                trigger_type="manual",
                status=status,
                raw_count=raw_count,
                cleaned_count=cleaned_count,
                saved_count=saved_count,
                detail_success_count=detail_result["detail_success_count"],
                detail_failed_count=detail_result["detail_failed_count"],
                error_message=error_message,
                started_at=started_at,
                finished_at=datetime.now(),
            )
            if status != "failed":
                rebuild_events(session)
                save_data_quality_snapshot(session)
        finally:
            session.close()

    return {
        "channel_code": channel_code,
        "status": status,
        "raw_count": raw_count,
        "cleaned_count": cleaned_count,
        "saved_count": saved_count,
        **detail_result,
    }


def _optional_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    parsed = _optional_positive_int(value)
    if parsed is None:
        parsed = default
    return max(minimum, min(maximum, parsed))

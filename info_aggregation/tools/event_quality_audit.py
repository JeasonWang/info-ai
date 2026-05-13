import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import Event, EventAnalysisRun, Info, LLMCallLog, get_session
from services.quality.data_quality import is_low_value_content


def _percent(part: int, total: int) -> float:
    return round(part * 100 / total, 2) if total else 0.0


def _channel_key(info: Info) -> str:
    return info.channel.code if info.channel else str(info.channel_id)


def _channel_quality(infos: list[Info]) -> dict:
    grouped: dict[str, list[Info]] = {}
    for info in infos:
        grouped.setdefault(_channel_key(info), []).append(info)
    result = {}
    for code, rows in sorted(grouped.items()):
        status_counter = Counter((row.detail_fetch_status or "unknown") for row in rows)
        avg_len = round(
            sum(row.detail_content_length or len(row.content or "") for row in rows) / max(len(rows), 1),
            1,
        )
        result[code] = {
            "total_count": len(rows),
            "complete_count": status_counter.get("complete", 0),
            "partial_count": status_counter.get("partial", 0),
            "list_only_count": status_counter.get("list_only", 0),
            "failed_count": status_counter.get("failed", 0),
            "pending_count": status_counter.get("pending", 0),
            "avg_content_length": avg_len,
            "complete_ratio": _percent(status_counter.get("complete", 0), len(rows)),
        }
    return result


def _event_quality(events: list[Event]) -> dict:
    active_events = [event for event in events if event.status == "active"]
    short_summary_count = sum(1 for event in active_events if len((event.one_line_summary or "").strip()) < 8)
    low_value_summary_count = sum(
        1 for event in active_events if is_low_value_content(event.title or "", event.one_line_summary or "")
    )
    single_source_active_count = sum(1 for event in active_events if (event.source_count or 0) <= 1)
    return {
        "event_count": len(events),
        "active_event_count": len(active_events),
        "short_summary_count": short_summary_count,
        "short_summary_ratio": _percent(short_summary_count, len(active_events)),
        "low_value_summary_count": low_value_summary_count,
        "low_value_summary_ratio": _percent(low_value_summary_count, len(active_events)),
        "single_source_active_count": single_source_active_count,
        "single_source_active_ratio": _percent(single_source_active_count, len(active_events)),
    }


def _analysis_quality(runs: list[EventAnalysisRun]) -> dict:
    fallback_count = sum(1 for run in runs if run.fallback_used or run.status == "fallback")
    provider_counter = Counter(run.provider or "unknown" for run in runs)
    return {
        "run_count": len(runs),
        "fallback_run_count": fallback_count,
        "fallback_run_ratio": _percent(fallback_count, len(runs)),
        "provider_counts": dict(sorted(provider_counter.items())),
    }


def _llm_quality(logs: list[LLMCallLog]) -> dict:
    failed_logs = [log for log in logs if log.status == "failed"]
    latest_failed = sorted(failed_logs, key=lambda log: log.created_at or 0, reverse=True)
    return {
        "call_count": len(logs),
        "failed_call_count": len(failed_logs),
        "failed_call_ratio": _percent(len(failed_logs), len(logs)),
        "latest_failure_reason": latest_failed[0].error_message if latest_failed else "",
    }


def build_event_quality_audit(session) -> dict:
    infos = session.query(Info).filter(Info.is_deleted == 0).all()
    events = session.query(Event).all()
    runs = session.query(EventAnalysisRun).all()
    llm_logs = session.query(LLMCallLog).all()
    return {
        "channels": _channel_quality(infos),
        "events": _event_quality(events),
        "analysis": _analysis_quality(runs),
        "llm": _llm_quality(llm_logs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit info-ai event data quality.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    session = get_session()
    try:
        report = build_event_quality_audit(session)
    finally:
        session.close()
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()

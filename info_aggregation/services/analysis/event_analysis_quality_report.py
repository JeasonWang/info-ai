from collections import defaultdict
from collections import Counter

from database import Event, EventAnalysisRun, EventItemLink, Info
from services.collection.acquisition_quality import build_acquisition_quality_profile


def _latest_runs_by_event(session) -> dict[int, EventAnalysisRun]:
    runs = (
        session.query(EventAnalysisRun)
        .order_by(EventAnalysisRun.event_id.asc(), EventAnalysisRun.created_at.desc(), EventAnalysisRun.id.desc())
        .all()
    )
    latest: dict[int, EventAnalysisRun] = {}
    for run in runs:
        latest.setdefault(run.event_id, run)
    return latest


def _linked_infos_by_event(session) -> dict[int, list[Info]]:
    rows = (
        session.query(EventItemLink.event_id, Info)
        .join(Info, Info.id == EventItemLink.item_id)
        .filter(Info.is_deleted == 0)
        .all()
    )
    grouped: dict[int, list[Info]] = defaultdict(list)
    for event_id, info in rows:
        grouped[event_id].append(info)
    return grouped


def _weak_source_count(infos: list[Info]) -> int:
    return sum(1 for info in infos if build_acquisition_quality_profile(info).needs_attention)


def _issue_reasons(event: Event, run: EventAnalysisRun | None, weak_count: int) -> list[str]:
    reasons: list[str] = []
    if run is None:
        return ["missing_analysis"]
    if run.status in {"failed", "fallback"} and run.failure_reason:
        reasons.append("llm_or_analysis_fallback")
    if (run.confidence or 0) < 0.6:
        reasons.append("low_confidence")
    if (run.quality_score or 0) < 60:
        reasons.append("low_quality_score")
    if run.fallback_used:
        reasons.append("fallback_used")
    if weak_count:
        reasons.append("weak_sources")
    if not (event.one_line_summary or "").strip():
        reasons.append("empty_one_line_summary")
    return reasons


def _governance_advice(reasons: list[str], weak_count: int) -> list[str]:
    advice: list[str] = []
    if "missing_analysis" in reasons:
        advice.append("先执行事件重建，补齐事件分析运行记录。")
    if "weak_sources" in reasons:
        advice.append(f"该事件有 {weak_count} 条弱来源，建议优先执行详情补偿后重新分析。")
    if "low_confidence" in reasons or "low_quality_score" in reasons:
        advice.append("分析置信度偏低，建议增加可用来源或启用大模型增强。")
    if "fallback_used" in reasons or "llm_or_analysis_fallback" in reasons:
        advice.append("大模型增强发生回退，检查模型服务地址、超时和模型输出格式。")
    if "empty_one_line_summary" in reasons:
        advice.append("一句话摘要为空，建议重新构建事件分析结果。")
    return advice or ["当前事件分析质量稳定，继续观察即可。"]


def _action_advice(reasons: list[str], weak_count: int) -> dict:
    if "missing_analysis" in reasons:
        return {"primary_issue": "缺少事件分析", "next_action": "执行事件重建或分析补偿"}
    if "weak_sources" in reasons:
        return {"primary_issue": "来源质量不足", "next_action": "先执行详情补偿，再重新分析该事件"}
    if "fallback_used" in reasons or "llm_or_analysis_fallback" in reasons:
        return {"primary_issue": "大模型分析回退", "next_action": "检查模型服务、超时和输出格式后重分析"}
    if "empty_one_line_summary" in reasons:
        return {"primary_issue": "一句话摘要缺失", "next_action": "重新构建事件分析结果"}
    if "low_confidence" in reasons or "low_quality_score" in reasons:
        return {"primary_issue": "分析置信度偏低", "next_action": "补充多源证据或启用大模型增强后重分析"}
    return {"primary_issue": "质量稳定", "next_action": "继续观察"}


def _risk_score(run: EventAnalysisRun | None, weak_count: int, reasons: list[str]) -> float:
    if run is None:
        return 100.0
    score = 0.0
    score += max(0.0, 60.0 - float(run.quality_score or 0))
    score += max(0.0, 0.6 - float(run.confidence or 0)) * 100
    score += min(30.0, weak_count * 12.0)
    score += 15.0 if run.fallback_used else 0.0
    score += 20.0 if run.status == "failed" else 0.0
    score += 10.0 if "empty_one_line_summary" in reasons else 0.0
    return round(score, 2)


def _display_quality_report(events: list[Event], limit: int) -> dict:
    status_counter = Counter(event.status or "unknown" for event in events)
    level_counter = Counter(event.display_quality_level or "unknown" for event in events)
    reason_counter: Counter[str] = Counter()
    blocked_samples: list[dict] = []

    for event in events:
        reasons = [reason.strip() for reason in (event.display_quality_reason or "").split(",") if reason.strip()]
        reason_counter.update(reasons)
        if (event.status or "") in {"monitoring", "low_quality"}:
            action = _display_action_advice(reasons)
            blocked_samples.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "one_line_summary": event.one_line_summary,
                    "status": event.status,
                    "source_count": event.source_count,
                    "display_quality_score": event.display_quality_score or 0,
                    "display_quality_level": event.display_quality_level or "",
                    "display_quality_reasons": reasons,
                    "primary_issue": action["primary_issue"],
                    "next_action": action["next_action"],
                    "last_updated_at": event.last_updated_at.strftime("%Y-%m-%d %H:%M:%S") if event.last_updated_at else "",
                }
            )

    blocked_samples.sort(key=lambda item: (item["display_quality_score"], -item["event_id"]))
    display_ready_count = status_counter.get("active", 0)
    blocked_count = status_counter.get("monitoring", 0) + status_counter.get("low_quality", 0)
    total_count = display_ready_count + blocked_count
    return {
        "summary": {
            "tracked_event_count": total_count,
            "display_ready_count": display_ready_count,
            "blocked_count": blocked_count,
            "display_ready_ratio": round(display_ready_count * 100 / total_count, 2) if total_count else 0,
            "status_counts": dict(sorted(status_counter.items())),
            "level_counts": dict(sorted(level_counter.items())),
            "top_block_reasons": [
                {"reason": reason, "count": count}
                for reason, count in reason_counter.most_common(8)
            ],
        },
        "blocked_samples": blocked_samples[:limit],
    }


def _display_action_advice(reasons: list[str]) -> dict:
    reason_set = set(reasons)
    if "mixed_unrelated_sources" in reason_set:
        return {"primary_issue": "疑似错合并", "next_action": "执行事件重建预演并拆分错误来源"}
    if "social_signal_without_fact_source" in reason_set:
        return {"primary_issue": "社交热度缺事实源", "next_action": "等待媒体或官方事实源后刷新展示质量"}
    if "single_weak_source" in reason_set:
        return {"primary_issue": "单一弱来源", "next_action": "补充可用事实源后刷新展示质量"}
    if "missing_complete_source" in reason_set or "missing_usable_source" in reason_set:
        return {"primary_issue": "缺少可用来源", "next_action": "执行详情补偿或二跳检索"}
    if "low_value_content" in reason_set:
        return {"primary_issue": "内容价值偏低", "next_action": "归档低价值内容或等待高质量来源"}
    if "empty_sources" in reason_set:
        return {"primary_issue": "缺少来源", "next_action": "重新构建事件来源关系"}
    return {"primary_issue": "展示质量不足", "next_action": "补充证据后刷新展示质量"}


def build_event_analysis_quality_report(session, limit: int = 20) -> dict:
    limit = max(1, min(limit, 100))
    tracked_events = (
        session.query(Event)
        .filter(Event.status.in_(("active", "monitoring", "low_quality")))
        .order_by(Event.last_updated_at.desc(), Event.id.desc())
        .all()
    )
    events = [event for event in tracked_events if event.status == "active"]
    latest_runs = _latest_runs_by_event(session)
    linked_infos = _linked_infos_by_event(session)

    risk_events: list[dict] = []
    analyzed_count = 0
    low_confidence_count = 0
    fallback_count = 0
    missing_analysis_count = 0
    weak_source_event_count = 0
    total_confidence = 0.0
    total_quality = 0.0

    for event in events:
        run = latest_runs.get(event.id)
        infos = linked_infos.get(event.id, [])
        weak_count = _weak_source_count(infos)
        reasons = _issue_reasons(event, run, weak_count)

        if run is None:
            missing_analysis_count += 1
        else:
            analyzed_count += 1
            total_confidence += float(run.confidence or 0)
            total_quality += float(run.quality_score or 0)
            if (run.confidence or 0) < 0.6:
                low_confidence_count += 1
            if run.fallback_used or run.status == "fallback":
                fallback_count += 1
        if weak_count:
            weak_source_event_count += 1

        if reasons:
            action = _action_advice(reasons, weak_count)
            risk_events.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "one_line_summary": event.one_line_summary,
                    "source_count": event.source_count,
                    "weak_source_count": weak_count,
                    "issue_reasons": reasons,
                    "governance_advice": _governance_advice(reasons, weak_count),
                    "primary_issue": action["primary_issue"],
                    "next_action": action["next_action"],
                    "risk_score": _risk_score(run, weak_count, reasons),
                    "run_id": run.id if run else None,
                    "mode": run.mode if run else "",
                    "provider": run.provider if run else "",
                    "model_name": run.model_name if run else "",
                    "status": run.status if run else "missing",
                    "quality_score": round(float(run.quality_score or 0), 2) if run else 0,
                    "confidence": round(float(run.confidence or 0), 4) if run else 0,
                    "fallback_used": bool(run.fallback_used) if run else False,
                    "failure_reason": run.failure_reason if run else "",
                    "last_analyzed_at": run.finished_at.strftime("%Y-%m-%d %H:%M:%S") if run and run.finished_at else "",
                }
            )

    risk_events.sort(key=lambda item: (-item["risk_score"], item["event_id"]))

    return {
        "summary": {
            "active_event_count": len(events),
            "analyzed_count": analyzed_count,
            "missing_analysis_count": missing_analysis_count,
            "low_confidence_count": low_confidence_count,
            "fallback_count": fallback_count,
            "weak_source_event_count": weak_source_event_count,
            "avg_confidence": round(total_confidence / analyzed_count, 4) if analyzed_count else 0,
            "avg_quality_score": round(total_quality / analyzed_count, 2) if analyzed_count else 0,
            "risk_event_count": len(risk_events),
        },
        "risk_events": risk_events[:limit],
        "display_quality": _display_quality_report(tracked_events, limit),
    }

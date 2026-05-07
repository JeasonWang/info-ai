from collections import Counter, defaultdict

from database import Channel, Info
from services.credential_provider import build_credential_report


def _percent(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count * 100 / total, 1)


def _is_seed(info: Info) -> bool:
    return (info.detail_strategy or "").strip().lower() == "seed"


def _is_complete(info: Info) -> bool:
    return (
        not _is_seed(info)
        and (info.detail_fetch_status or "").strip() == "complete"
        and (info.detail_score or 0) >= 70
        and (info.detail_content_length or len(info.content or "")) >= 40
    )


def _is_high_value_partial(info: Info) -> bool:
    return (
        not _is_seed(info)
        and (info.detail_fetch_status or "").strip() == "partial"
        and (info.detail_score or 0) >= 60
        and (info.detail_content_length or len(info.content or "")) >= 80
    )


def _needs_attention(info: Info) -> bool:
    if _is_seed(info):
        return False
    status = (info.detail_fetch_status or "").strip()
    return (
        status in {"failed", "list_only", "pending", ""}
        or (info.detail_score or 0) < 60
        or (info.detail_content_length or len(info.content or "")) < 40
    )


def _sample(info: Info) -> dict:
    return {
        "id": info.id,
        "title": info.title,
        "source_url": info.source_url,
        "detail_fetch_status": info.detail_fetch_status,
        "detail_strategy": info.detail_strategy,
        "detail_score": info.detail_score,
        "detail_content_length": info.detail_content_length or len(info.content or ""),
        "detail_fetch_error": info.detail_fetch_error,
    }


def build_channel_quality_report(session, sample_limit: int = 5) -> dict:
    """按渠道输出真实采集详情质量，明确哪些渠道还不能支撑产品展示。"""

    channels = session.query(Channel).order_by(Channel.id.asc()).all()
    credential_report = build_credential_report([channel.code for channel in channels])
    rows = []

    for channel in channels:
        infos = (
            session.query(Info)
            .filter(Info.channel_id == channel.id, Info.is_deleted == 0)
            .order_by(Info.event_time.desc(), Info.created_at.desc(), Info.id.desc())
            .limit(100)
            .all()
        )
        real_infos = [info for info in infos if not _is_seed(info)]
        complete_count = sum(1 for info in real_infos if _is_complete(info))
        high_value_partial_count = sum(1 for info in real_infos if _is_high_value_partial(info))
        attention_infos = [info for info in real_infos if _needs_attention(info)]
        failure_counter = Counter((info.detail_fetch_error or info.detail_fetch_status or "unknown") for info in attention_infos)
        strategy_counter = Counter((info.detail_strategy or "unknown") for info in real_infos)
        avg_score = round(sum((info.detail_score or 0) for info in real_infos) / len(real_infos), 1) if real_infos else 0
        avg_length = round(
            sum((info.detail_content_length or len(info.content or "")) for info in real_infos) / len(real_infos),
            1,
        ) if real_infos else 0

        usable_count = complete_count + high_value_partial_count
        rows.append(
            {
                "channel_id": channel.id,
                "channel_code": channel.code,
                "channel_name": channel.name,
                "total_count": len(infos),
                "real_count": len(real_infos),
                "seed_count": len(infos) - len(real_infos),
                "complete_count": complete_count,
                "complete_ratio": _percent(complete_count, len(real_infos)),
                "high_value_partial_count": high_value_partial_count,
                "usable_count": usable_count,
                "usable_ratio": _percent(usable_count, len(real_infos)),
                "needs_attention_count": len(attention_infos),
                "needs_attention_ratio": _percent(len(attention_infos), len(real_infos)),
                "avg_detail_score": avg_score,
                "avg_detail_content_length": avg_length,
                "top_failure_reasons": [
                    {"reason": reason, "count": count}
                    for reason, count in failure_counter.most_common(5)
                ],
                "top_detail_strategies": [
                    {"strategy": strategy, "count": count}
                    for strategy, count in strategy_counter.most_common(5)
                ],
                "credential_health": credential_report.get(channel.code, {"health": "not_required"}),
                "weak_samples": [_sample(info) for info in sorted(
                    attention_infos,
                    key=lambda item: (item.detail_score or 0, item.detail_content_length or len(item.content or "")),
                )[:sample_limit]],
            }
        )

    summary = _build_summary(rows)
    return {"summary": summary, "channels": rows}


def _build_summary(rows: list[dict]) -> dict:
    totals = defaultdict(int)
    for row in rows:
        for key in ("real_count", "complete_count", "high_value_partial_count", "usable_count", "needs_attention_count"):
            totals[key] += int(row.get(key, 0))
    weak_channels = [
        {
            "channel_code": row["channel_code"],
            "channel_name": row["channel_name"],
            "usable_ratio": row["usable_ratio"],
            "needs_attention_ratio": row["needs_attention_ratio"],
        }
        for row in sorted(rows, key=lambda item: (item["usable_ratio"], -item["needs_attention_ratio"]))[:5]
        if row["real_count"] > 0
    ]
    return {
        "real_count": totals["real_count"],
        "complete_count": totals["complete_count"],
        "high_value_partial_count": totals["high_value_partial_count"],
        "usable_count": totals["usable_count"],
        "needs_attention_count": totals["needs_attention_count"],
        "complete_ratio": _percent(totals["complete_count"], totals["real_count"]),
        "usable_ratio": _percent(totals["usable_count"], totals["real_count"]),
        "needs_attention_ratio": _percent(totals["needs_attention_count"], totals["real_count"]),
        "weak_channels": weak_channels,
    }

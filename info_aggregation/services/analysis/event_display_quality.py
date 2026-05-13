from dataclasses import dataclass, field
from collections import Counter

from database import Event, EventItemLink, Info
from services.collection.acquisition_quality import build_acquisition_quality_profile
from services.quality.data_quality import is_low_value_content


SOCIAL_SIGNAL_CHANNELS = {"weibo", "xiaohongshu"}
SOCIAL_FACT_MARKERS = (
    "官方",
    "通报",
    "警方",
    "消防",
    "医院",
    "法院",
    "应急",
    "救援",
    "伤亡",
    "事故",
    "调查",
    "声明",
    "回应",
    "发布",
    "宣布",
    "记者",
    "媒体",
    "报道称",
    "数据显示",
    "报告",
    "根据",
)


@dataclass(frozen=True)
class EventDisplayQuality:
    status: str
    score: int
    level: str
    reasons: list[str] = field(default_factory=list)

    @property
    def reason_text(self) -> str:
        return ",".join(self.reasons)


def _channel_code(item: Info) -> str:
    return item.channel.code if getattr(item, "channel", None) else ""


def _has_social_fact_signal(item: Info) -> bool:
    if _channel_code(item) not in SOCIAL_SIGNAL_CHANNELS:
        return True
    text = f"{item.title or ''} {item.content or ''}"
    return any(marker in text for marker in SOCIAL_FACT_MARKERS)


def evaluate_event_display_quality(items: list[Info], analysis_quality_score: float = 0.0) -> EventDisplayQuality:
    """判断事件是否足够可信，可进入用户端信息流。"""

    if not items:
        return EventDisplayQuality(status="low_quality", score=0, level="blocked", reasons=["empty_sources"])

    profiles = [build_acquisition_quality_profile(item) for item in items]
    source_count = len({item.id for item in items if item.id}) or len(items)
    channel_count = len({_channel_code(item) or str(item.channel_id) for item in items})
    usable_count = sum(
        1
        for item, profile in zip(items, profiles)
        if profile.usable or ((item.detail_fetch_status or "") in {"complete", "partial"} and (item.detail_score or 0) >= 60)
    )
    complete_count = sum(
        1
        for item, profile in zip(items, profiles)
        if profile.status == "complete" or ((item.detail_fetch_status or "") == "complete" and (item.detail_score or 0) >= 70)
    )
    low_value_count = sum(1 for item in items if is_low_value_content(item.title or "", item.content or ""))
    social_only = all(_channel_code(item) in SOCIAL_SIGNAL_CHANNELS for item in items)
    social_fact_count = sum(1 for item in items if _has_social_fact_signal(item))
    social_without_fact_source = social_only and social_fact_count == 0
    avg_completeness = int(sum(profile.completeness_score for profile in profiles) / max(len(profiles), 1))

    score = 20
    score += min(30, source_count * 10)
    score += min(25, complete_count * 18)
    score += min(15, usable_count * 8)
    score += min(10, channel_count * 4)
    score += min(10, int(max(analysis_quality_score, 0) / 10))
    score += min(10, int(avg_completeness / 10))
    if complete_count >= 1 and low_value_count == 0:
        score += 5
    score -= low_value_count * 30
    if social_without_fact_source:
        score -= 20
    score = max(0, min(100, score))

    reasons: list[str] = []
    if source_count <= 1 and usable_count == 0:
        reasons.append("single_weak_source")
    if low_value_count:
        reasons.append("low_value_content")
    if social_without_fact_source:
        reasons.append("social_signal_without_fact_source")
    if complete_count == 0:
        reasons.append("missing_complete_source")
    if usable_count == 0:
        reasons.append("missing_usable_source")

    has_meaningful_non_social_source = (
        not social_only
        and low_value_count == 0
        and any(len((item.content or "").strip()) >= 20 for item in items)
    )

    if social_without_fact_source:
        status = "monitoring"
    elif complete_count >= 1 and (source_count >= 2 or usable_count >= 1) and low_value_count == 0:
        status = "active"
    elif has_meaningful_non_social_source:
        status = "active"
    elif score >= 70 and usable_count >= 1 and low_value_count == 0:
        status = "active"
    elif "low_value_content" in reasons or "single_weak_source" in reasons:
        status = "monitoring"
    else:
        status = "monitoring"

    if score >= 85:
        level = "excellent"
    elif score >= 70:
        level = "good"
    elif score >= 35 or status == "monitoring":
        level = "weak"
    else:
        level = "blocked"

    return EventDisplayQuality(status=status, score=score, level=level, reasons=list(dict.fromkeys(reasons)))


def _load_event_items(session, event_id: int) -> list[Info]:
    return (
        session.query(Info)
        .join(EventItemLink, EventItemLink.item_id == Info.id)
        .filter(EventItemLink.event_id == event_id, Info.is_deleted == 0)
        .order_by(EventItemLink.is_primary.desc(), EventItemLink.weight.desc(), EventItemLink.id.asc())
        .all()
    )


def backfill_event_display_quality(
    session,
    limit: int | None = None,
    statuses: tuple[str, ...] = ("active", "monitoring", "low_quality"),
) -> dict:
    """回填已有事件的展示质量字段，并按质量结果调整用户端展示状态。"""

    query = (
        session.query(Event)
        .filter(Event.status.in_(statuses))
        .order_by(Event.last_updated_at.desc(), Event.id.desc())
    )
    if limit:
        query = query.limit(limit)

    events = query.all()
    status_counter: Counter[str] = Counter()
    processed_count = 0
    changed_count = 0

    for event in events:
        items = _load_event_items(session, event.id)
        quality = evaluate_event_display_quality(items)
        before = (
            event.status or "",
            event.display_quality_score or 0,
            event.display_quality_level or "",
            event.display_quality_reason or "",
        )

        event.status = quality.status
        event.display_quality_score = quality.score
        event.display_quality_level = quality.level
        event.display_quality_reason = quality.reason_text

        after = (
            event.status or "",
            event.display_quality_score or 0,
            event.display_quality_level or "",
            event.display_quality_reason or "",
        )
        processed_count += 1
        changed_count += int(before != after)
        status_counter[event.status or "unknown"] += 1

    session.commit()
    return {
        "processed_count": processed_count,
        "changed_count": changed_count,
        "status_counts": dict(sorted(status_counter.items())),
    }

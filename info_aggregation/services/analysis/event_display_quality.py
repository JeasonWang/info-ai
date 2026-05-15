from dataclasses import dataclass, field
from collections import Counter
from difflib import SequenceMatcher

from sqlalchemy import or_

from database import Event, EventAnalysisRun, EventItemLink, Info
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
    "声明",
    "新华社",
    "央视新闻",
    "央视财经",
    "央视网",
    "央广",
    "财联社",
    "澎湃",
    "路透",
    "Reuters",
    "报道称",
    "数据显示",
    "调查报告",
)

LOW_VALUE_HOT_TITLE_MARKERS = (
    "鲜花接机",
    "接机爸爸",
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


def _has_low_value_hot_title(item: Info) -> bool:
    category_code = item.category.code if getattr(item, "category", None) else ""
    if category_code != "hot":
        return False
    title = item.title or ""
    return any(marker in title for marker in LOW_VALUE_HOT_TITLE_MARKERS)


def _normalize_title_for_consistency(value: str) -> str:
    normalized = "".join((value or "").lower().split())
    for word in ("微博热搜", "热搜", "话题", "回应", "发布", "宣布", "相关", "事件", "讨论"):
        normalized = normalized.replace(word, "")
    return normalized.strip(" #，。:：-—_")


def _shared_title_anchor_count(left: str, right: str) -> int:
    ignored = {"进展", "后续", "关注", "正在", "持续", "情况", "原因", "事故", "救援"}
    left_anchors = {
        left[index : index + 2]
        for index in range(max(len(left) - 1, 0))
        if left[index : index + 2] not in ignored
    }
    right_anchors = {
        right[index : index + 2]
        for index in range(max(len(right) - 1, 0))
        if right[index : index + 2] not in ignored
    }
    return len(left_anchors & right_anchors)


def _title_similarity(left: str, right: str) -> float:
    left_normalized = _normalize_title_for_consistency(left)
    right_normalized = _normalize_title_for_consistency(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized in right_normalized or right_normalized in left_normalized:
        return 1.0
    if _shared_title_anchor_count(left_normalized, right_normalized) >= 2:
        return 0.36
    return SequenceMatcher(None, left_normalized, right_normalized).ratio()


def _has_mixed_unrelated_sources(items: list[Info]) -> bool:
    """识别历史错合并导致的同一事件内无关来源串台。"""

    meaningful_titles = [
        item.title or ""
        for item in items
        if len(_normalize_title_for_consistency(item.title or "")) >= 4
    ]
    unique_titles = list(dict.fromkeys(meaningful_titles))
    if len(unique_titles) < 2:
        return False

    unrelated_pairs = 0
    pair_count = 0
    for index, left in enumerate(unique_titles):
        for right in unique_titles[index + 1 :]:
            pair_count += 1
            if _title_similarity(left, right) < 0.35:
                unrelated_pairs += 1

    if pair_count == 0:
        return False
    return unrelated_pairs / pair_count >= 0.45


def _is_social_without_fact(items: list[Info]) -> bool:
    return bool(items) and all(_channel_code(item) in SOCIAL_SIGNAL_CHANNELS for item in items) and not any(
        _has_social_fact_signal(item) for item in items
    )


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
    low_value_flags = [
        is_low_value_content(item.title or "", item.content or "") or _has_low_value_hot_title(item)
        for item in items
    ]
    low_value_count = sum(1 for value in low_value_flags if value)
    has_complete_fact_source = any(
        _channel_code(item) not in SOCIAL_SIGNAL_CHANNELS
        and not is_low_value
        and (
            profile.status == "complete"
            or ((item.detail_fetch_status or "") == "complete" and (item.detail_score or 0) >= 70)
        )
        for item, profile, is_low_value in zip(items, profiles, low_value_flags)
    )
    blocking_low_value_count = 0 if has_complete_fact_source else low_value_count
    social_only = all(_channel_code(item) in SOCIAL_SIGNAL_CHANNELS for item in items)
    social_fact_count = sum(1 for item in items if _has_social_fact_signal(item))
    social_without_fact_source = social_only and social_fact_count == 0
    mixed_unrelated_sources = _has_mixed_unrelated_sources(items)
    avg_completeness = int(sum(profile.completeness_score for profile in profiles) / max(len(profiles), 1))

    score = 20
    score += min(30, source_count * 10)
    score += min(25, complete_count * 18)
    score += min(15, usable_count * 8)
    score += min(10, channel_count * 4)
    score += min(10, int(max(analysis_quality_score, 0) / 10))
    score += min(10, int(avg_completeness / 10))
    if complete_count >= 1 and blocking_low_value_count == 0:
        score += 5
    score -= blocking_low_value_count * 30
    if social_without_fact_source:
        score -= 20
    score = max(0, min(100, score))

    reasons: list[str] = []
    if source_count <= 1 and usable_count == 0:
        reasons.append("single_weak_source")
    if blocking_low_value_count:
        reasons.append("low_value_content")
    if social_without_fact_source:
        reasons.append("social_signal_without_fact_source")
    if mixed_unrelated_sources:
        reasons.append("mixed_unrelated_sources")
    if complete_count == 0:
        reasons.append("missing_complete_source")
    if usable_count == 0:
        reasons.append("missing_usable_source")

    has_meaningful_non_social_source = (
        not social_only
        and blocking_low_value_count == 0
        and any(len((item.content or "").strip()) >= 20 for item in items)
    )

    if mixed_unrelated_sources:
        status = "monitoring"
    elif complete_count == 0:
        status = "monitoring"
    elif social_without_fact_source:
        status = "monitoring"
    elif complete_count >= 1 and (source_count >= 2 or usable_count >= 1) and blocking_low_value_count == 0:
        status = "active"
    elif has_meaningful_non_social_source:
        status = "active"
    elif score >= 70 and usable_count >= 1 and blocking_low_value_count == 0:
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


def _fact_source_match_score(target_titles: list[str], candidate: Info) -> float:
    candidate_title = candidate.title or ""
    title_score = max((_title_similarity(title, candidate_title) for title in target_titles if title), default=0.0)
    content = f"{candidate.title or ''} {candidate.content or ''}"
    fact_bonus = 0.08 if any(marker in content for marker in SOCIAL_FACT_MARKERS) else 0.0
    profile = build_acquisition_quality_profile(candidate)
    quality_bonus = 0.06 if profile.usable else 0.0
    return min(1.0, title_score + fact_bonus + quality_bonus)


def _find_secondary_fact_sources(session, items: list[Info], limit: int = 2) -> list[Info]:
    if not _is_social_without_fact(items):
        return []
    existing_ids = {item.id for item in items if item.id}
    target_titles = [item.title or "" for item in items]
    candidates = (
        session.query(Info)
        .filter(or_(Info.is_deleted == 0, Info.is_deleted.is_(None)), ~Info.id.in_(existing_ids))
        .order_by(Info.event_time.desc(), Info.id.desc())
        .limit(300)
        .all()
    )
    scored: list[tuple[float, Info]] = []
    for candidate in candidates:
        if _channel_code(candidate) in SOCIAL_SIGNAL_CHANNELS:
            continue
        profile = build_acquisition_quality_profile(candidate)
        if not profile.usable and not (
            (candidate.detail_fetch_status or "") in {"complete", "partial"} and (candidate.detail_score or 0) >= 70
        ):
            continue
        score = _fact_source_match_score(target_titles, candidate)
        if score >= 0.62:
            scored.append((score, candidate))
    scored.sort(key=lambda item: (-item[0], -(item[1].detail_score or 0), item[1].id))
    return [candidate for _, candidate in scored[:limit]]


def _mark_event_analysis_stale(session, event_id: int, reason: str) -> int:
    latest_run = (
        session.query(EventAnalysisRun)
        .filter(EventAnalysisRun.event_id == event_id)
        .order_by(EventAnalysisRun.created_at.desc(), EventAnalysisRun.id.desc())
        .first()
    )
    if not latest_run or latest_run.status == "stale":
        return 0
    latest_run.status = "stale"
    latest_run.failure_reason = reason
    return 1


def link_secondary_fact_sources_for_social_events(session, limit: int = 50) -> dict:
    """为纯社交线索补充库内已采到的事实源，降低观察中事件的来源缺口。"""

    limit = max(1, min(limit, 200))
    events = (
        session.query(Event)
        .filter(Event.status.in_(("active", "monitoring")))
        .order_by(Event.last_updated_at.desc(), Event.id.desc())
        .limit(limit)
        .all()
    )
    linked_count = 0
    updated_event_count = 0
    samples: list[dict] = []

    for event in events:
        items = _load_event_items(session, event.id)
        if not _is_social_without_fact(items):
            continue
        existing_ids = {item.id for item in items if item.id}
        candidates = _find_secondary_fact_sources(session, items)
        added: list[Info] = []
        for candidate in candidates:
            if candidate.id in existing_ids:
                continue
            session.add(EventItemLink(event_id=event.id, item_id=candidate.id, role="fact_source", is_primary=0, weight=85))
            existing_ids.add(candidate.id)
            added.append(candidate)
            linked_count += 1
        if not added:
            continue
        _mark_event_analysis_stale(session, event.id, reason="fact_source_linked_for_source_quality_governance")
        updated_items = [*items, *added]
        quality = evaluate_event_display_quality(updated_items)
        event.source_count = len(existing_ids)
        event.display_quality_score = quality.score
        event.display_quality_level = quality.level
        event.display_quality_reason = quality.reason_text
        event.status = quality.status
        updated_event_count += 1
        samples.append(
            {
                "event_id": event.id,
                "title": event.title,
                "linked_info_ids": [item.id for item in added],
                "status": event.status,
                "display_quality_score": event.display_quality_score,
            }
        )

    session.commit()
    return {"processed_count": len(events), "updated_event_count": updated_event_count, "linked_count": linked_count, "samples": samples}


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

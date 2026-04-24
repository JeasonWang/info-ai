from collections import defaultdict
from difflib import SequenceMatcher
import hashlib

from sqlalchemy import inspect

from database import Event, EventItemLink, EventSummarySnapshot, EventTimelineEntry, Info


TECH_TOPIC_LABELS = {
    "chip_release": "芯片发布",
    "model_release": "模型发布",
    "dev_tool": "开发工具",
}


def _build_event_key(item: Info) -> tuple[int, str]:
    anchor = (item.core_entity or item.title[:16]).strip().lower()
    return item.category_id, anchor


def _build_event_key_value(category_id: int, anchor: str) -> str:
    """生成事件稳定键，保证同一分类下同一核心实体重建时能命中同一事件。"""

    raw_key = f"{category_id}:{_normalize_summary_text(anchor).lower()}"
    return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()


def _text_similarity(left: str, right: str) -> float:
    normalized_left = _normalize_summary_text(left)
    normalized_right = _normalize_summary_text(right)
    if not normalized_left or not normalized_right:
        return 0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _is_low_quality_item(item: Info) -> bool:
    content = _normalize_summary_text(item.content)
    if item.detail_fetch_status in {"failed", "list_only"} and len(content) < 30:
        return True
    if len(content) < 12:
        return True
    return _text_similarity(item.title, content) >= 0.94 and len(content) <= len(item.title) + 8


def _quality_score(item: Info) -> float:
    content = _normalize_summary_text(item.content)
    status_bonus = {
        "complete": 45,
        "partial": 25,
        "list_only": 5,
        "failed": -40,
        "pending": 0,
    }.get(item.detail_fetch_status or "", 0)
    length_bonus = min(len(content) / 4, 35)
    detail_score = (item.detail_score or 0) / 4
    duplicate_penalty = 35 if _text_similarity(item.title, content) >= 0.9 else 0
    return status_bonus + length_bonus + detail_score - duplicate_penalty


def _split_csv(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _collect_top_values(items: list[Info], attr_name: str, limit: int = 3) -> list[str]:
    counter: dict[str, int] = {}
    for item in items:
        raw_value = getattr(item, attr_name, "") or ""
        for value in _split_csv(raw_value):
            counter[value] = counter.get(value, 0) + 1
    return [value for value, _ in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _collect_top_topic(items: list[Info]) -> str:
    counter: dict[str, int] = {}
    for item in items:
        if not item.tech_topic_type:
            continue
        counter[item.tech_topic_type] = counter.get(item.tech_topic_type, 0) + 1
    if not counter:
        return ""
    topic_type = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return TECH_TOPIC_LABELS.get(topic_type, topic_type)


def _build_one_line(items: list[Info]) -> str:
    entity = items[0].core_entity or items[0].title[:12]
    topic_label = _collect_top_topic(items)
    source_count = len(items)
    topic_phrase = f"{entity} 的{topic_label}" if topic_label else f"{entity} 相关"

    if source_count <= 1:
        lead_content = _normalize_summary_text(items[0].content[:120])
        title = _normalize_summary_text(items[0].title)
        if lead_content:
            if title and lead_content.startswith(title):
                lead_content = lead_content[len(title):].lstrip("，。,:：;； ")
            if lead_content:
                return lead_content
        return f"{topic_phrase}内容正在引发关注。"
    if source_count <= 3:
        return f"{topic_phrase}讨论正在升温，已出现多来源跟进。"
    return f"{topic_phrase}讨论持续升温，已聚合 {source_count} 条来源内容。"


def _build_what_happened(items: list[Info]) -> str:
    lead_item = items[0]
    lead_content = _normalize_summary_text(lead_item.content[:180])
    top_keywords = _collect_top_values(items, "tech_keywords", limit=2)
    if lead_content and top_keywords:
        return f"{lead_content} 当前讨论主要围绕 {'、'.join(top_keywords)} 展开。"
    return lead_content or "暂时还没有提炼出事件摘要。"


def _build_why_it_matters(items: list[Info]) -> str:
    source_count = len({item.channel_id for item in items})
    top_entities = _collect_top_values(items, "tech_entities", limit=2)
    top_keywords = _collect_top_values(items, "tech_keywords", limit=2)

    if top_entities and top_keywords:
        return (
            f"这条事件已扩散到 {source_count} 个来源，讨论集中在 {'、'.join(top_entities)} "
            f"以及 {'、'.join(top_keywords)} 等技术点，说明它正在形成跨平台的持续影响。"
        )

    if top_entities:
        return f"这条事件已扩散到 {source_count} 个来源，且多个平台都在持续关注 {'、'.join(top_entities)}，说明它不再只是零散讨论。"

    return f"这条事件已扩散到 {source_count} 个来源，说明它不再只是单个平台的零散讨论。"


def _normalize_summary_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _build_latest_update(items: list[Info]) -> str:
    latest_item = items[-1]
    lead_item = items[0]
    latest_content = _normalize_summary_text(latest_item.content[:180])
    lead_content = _normalize_summary_text(lead_item.content[:180])
    latest_keywords = _split_csv(latest_item.tech_keywords)

    # 如果事件首条和最新一条内容几乎一致，说明还没有提炼出真正的增量进展，
    # 这里返回更明确的状态语句，避免前端出现“重点结论”和“最新进展”完全重复。
    if not latest_content:
        return "当前暂无明确新增进展，事件仍在持续发酵。"

    if latest_content == lead_content:
        if len(items) > 1:
            if latest_keywords:
                return f"最新一轮更新继续聚焦 {'、'.join(latest_keywords[:2])}，当前讨论仍围绕同一核心事实延伸。"
            return f"最新一轮更新来自 {latest_item.title}，当前讨论仍围绕同一核心事实延伸。"
        return "当前暂无明确新增进展，事件仍在持续发酵。"

    if latest_keywords:
        return f"{latest_content} 当前新增讨论重点集中在 {'、'.join(latest_keywords[:2])}。"

    return latest_content


def _load_existing_events(session) -> dict[str, Event]:
    """按稳定键加载已有事件，用于重建时复用原事件ID。"""

    table_names = set(inspect(session.get_bind()).get_table_names())
    if "event" not in table_names:
        return {}
    columns = {column["name"] for column in inspect(session.get_bind()).get_columns("event")}
    if "event_key" not in columns:
        return {}
    return {event.event_key: event for event in session.query(Event).filter(Event.event_key != "").all()}


def rebuild_events(session, limit: int = 200):
    items = (
        session.query(Info)
        .filter(Info.is_deleted == 0)
        .order_by(Info.event_time.desc(), Info.created_at.desc(), Info.id.desc())
        .limit(limit)
        .all()
    )

    grouped_items: dict[tuple[int, str], list[Info]] = defaultdict(list)
    for item in items:
        if _is_low_quality_item(item):
            continue
        grouped_items[_build_event_key(item)].append(item)

    existing_events = _load_existing_events(session)
    session.query(EventItemLink).delete()
    session.query(EventTimelineEntry).delete()
    session.query(EventSummarySnapshot).delete()
    session.query(Event).update({Event.status: "archived"}, synchronize_session="fetch")
    session.flush()

    for (category_id, anchor), group in grouped_items.items():
        group.sort(key=lambda item: item.event_time or item.created_at)
        lead_item = sorted(group, key=_quality_score, reverse=True)[0]
        group = [lead_item] + [item for item in group if item.id != lead_item.id]
        lead_item = group[0]
        latest_item = group[-1]
        event_key = _build_event_key_value(category_id, anchor)
        event = existing_events.get(event_key) or Event(event_key=event_key)
        event.title = lead_item.title
        event.one_line_summary = _build_one_line(group)
        event.primary_category_id = lead_item.category_id
        event.status = "active"
        event.heat_score = min(100, 60 + len(group) * 10)
        event.freshness_score = 90
        event.composite_score = min(100, 70 + len(group) * 8)
        event.source_count = len(group)
        event.started_at = lead_item.event_time or lead_item.created_at
        event.last_updated_at = latest_item.event_time or latest_item.created_at
        event.event_key = event_key
        if event.id is None:
            session.add(event)
        session.flush()

        session.add_all(
            [
                EventSummarySnapshot(
                    event_id=event.id,
                    summary_type="one_line",
                    content=event.one_line_summary,
                    version=1,
                ),
                EventSummarySnapshot(
                    event_id=event.id,
                    summary_type="what_happened",
                    content=_build_what_happened(group),
                    version=1,
                ),
                EventSummarySnapshot(
                    event_id=event.id,
                    summary_type="why_it_matters",
                    content=_build_why_it_matters(group),
                    version=1,
                ),
                EventSummarySnapshot(
                    event_id=event.id,
                    summary_type="latest_update",
                    content=_build_latest_update(group),
                    version=1,
                ),
            ]
        )

        for index, item in enumerate(group, start=1):
            session.add(
                EventItemLink(
                    event_id=event.id,
                    item_id=item.id,
                    role="primary" if index == 1 else "media",
                    is_primary=1 if index == 1 else 0,
                    weight=max(10, 100 - index * 10),
                )
            )
            session.add(
                EventTimelineEntry(
                    event_id=event.id,
                    occurred_at=item.event_time or item.created_at,
                    summary=item.content[:80],
                    source_item_id=item.id,
                    confidence=0.8,
                    display_order=index,
                )
            )

    session.commit()

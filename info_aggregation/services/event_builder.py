from collections import defaultdict

from database import Event, EventItemLink, EventSummarySnapshot, EventTimelineEntry, Info


def _build_event_key(item: Info) -> tuple[int, str]:
    anchor = (item.core_entity or item.title[:16]).strip().lower()
    return item.category_id, anchor


def _build_one_line(items: list[Info]) -> str:
    entity = items[0].core_entity or items[0].title[:12]
    return f"{entity} 相关讨论正在升温，当前已聚合 {len(items)} 条来源内容。"


def _build_why_it_matters(items: list[Info]) -> str:
    source_count = len({item.channel_id for item in items})
    return f"这条事件已扩散到 {source_count} 个来源，说明它不再只是单个平台的零散讨论。"


def _normalize_summary_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _build_latest_update(items: list[Info]) -> str:
    latest_item = items[-1]
    lead_item = items[0]
    latest_content = _normalize_summary_text(latest_item.content[:180])
    lead_content = _normalize_summary_text(lead_item.content[:180])

    # 如果事件首条和最新一条内容几乎一致，说明还没有提炼出真正的增量进展，
    # 这里返回更明确的状态语句，避免前端出现“重点结论”和“最新进展”完全重复。
    if not latest_content:
        return "当前暂无明确新增进展，事件仍在持续发酵。"

    if latest_content == lead_content:
        if len(items) > 1:
            return f"最新一轮更新来自 {latest_item.title}，当前讨论仍围绕同一核心事实延伸。"
        return "当前暂无明确新增进展，事件仍在持续发酵。"

    return latest_content


def rebuild_events(session, limit: int = 200):
    items = (
        session.query(Info)
        .filter(Info.is_deleted == 0)
        .order_by(Info.event_time.asc(), Info.created_at.asc())
        .limit(limit)
        .all()
    )

    grouped_items: dict[tuple[int, str], list[Info]] = defaultdict(list)
    for item in items:
        grouped_items[_build_event_key(item)].append(item)

    session.query(EventItemLink).delete()
    session.query(EventTimelineEntry).delete()
    session.query(EventSummarySnapshot).delete()
    session.query(Event).delete()
    session.flush()

    for _, group in grouped_items.items():
        group.sort(key=lambda item: item.event_time or item.created_at)
        lead_item = group[0]
        latest_item = group[-1]
        event = Event(
            title=lead_item.title,
            one_line_summary=_build_one_line(group),
            primary_category_id=lead_item.category_id,
            status="active",
            heat_score=min(100, 60 + len(group) * 10),
            freshness_score=90,
            composite_score=min(100, 70 + len(group) * 8),
            source_count=len(group),
            started_at=lead_item.event_time or lead_item.created_at,
            last_updated_at=latest_item.event_time or latest_item.created_at,
        )
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
                    content=lead_item.content[:180],
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

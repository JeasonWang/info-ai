import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import Event, Info, get_session
from services.analysis.event_builder import (
    _build_event_key_value,
    _group_related_items,
    _is_low_quality_item,
)


def _percent(part: int, total: int) -> float:
    return round(part * 100 / total, 2) if total else 0.0


def _channel_code(item: Info) -> str:
    return item.channel.code if item.channel else str(item.channel_id)


def preview_event_rebuild(session, limit: int = 300) -> dict:
    """Preview latest-info event grouping without mutating events or links."""

    limit = max(1, min(limit, 2000))
    infos = (
        session.query(Info)
        .filter(Info.is_deleted == 0)
        .order_by(Info.event_time.desc(), Info.created_at.desc(), Info.id.desc())
        .limit(limit)
        .all()
    )
    usable_infos = [item for item in infos if not _is_low_quality_item(item)]
    grouped_items = _group_related_items(usable_infos)
    event_keys = {
        _build_event_key_value(category_id, anchor)
        for category_id, anchor in grouped_items.keys()
    }
    existing_events = {
        event.event_key: event
        for event in session.query(Event).filter(Event.event_key.in_(event_keys)).all()
        if event.event_key
    }

    group_sizes = Counter(len(items) for items in grouped_items.values())
    multi_source_groups = [
        items
        for items in grouped_items.values()
        if len({_channel_code(item) for item in items}) > 1
    ]
    matched_statuses = Counter(
        existing_events[key].status
        for key in event_keys
        if key in existing_events
    )
    sample_groups = []
    for (category_id, anchor), items in sorted(
        grouped_items.items(),
        key=lambda entry: (-len(entry[1]), entry[0][0], entry[0][1]),
    )[:10]:
        key = _build_event_key_value(category_id, anchor)
        sample_groups.append(
            {
                "anchor": anchor,
                "category_id": category_id,
                "source_count": len(items),
                "channel_count": len({_channel_code(item) for item in items}),
                "channels": sorted({_channel_code(item) for item in items}),
                "matched_event_status": existing_events[key].status if key in existing_events else "",
                "titles": [item.title for item in items[:3]],
            }
        )

    return {
        "sampled_info_count": len(infos),
        "usable_info_count": len(usable_infos),
        "usable_info_ratio": _percent(len(usable_infos), len(infos)),
        "candidate_group_count": len(grouped_items),
        "single_item_group_count": group_sizes.get(1, 0),
        "single_item_group_ratio": _percent(group_sizes.get(1, 0), len(grouped_items)),
        "multi_item_group_count": len(grouped_items) - group_sizes.get(1, 0),
        "multi_source_group_count": len(multi_source_groups),
        "multi_source_group_ratio": _percent(len(multi_source_groups), len(grouped_items)),
        "matched_existing_event_count": sum(matched_statuses.values()),
        "matched_existing_event_statuses": dict(sorted(matched_statuses.items())),
        "sample_groups": sample_groups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview event rebuild grouping without writing data.")
    parser.add_argument("--limit", type=int, default=300, help="Latest info rows to sample. Default: 300.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    session = get_session()
    try:
        result = preview_event_rebuild(session, limit=args.limit)
    finally:
        session.close()

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()

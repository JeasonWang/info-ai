import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawlers.reuters import ReutersCrawler
from database import Channel, Info, get_session
from scheduler import _apply_info_semantics, _record_info_acquisition_log


def backfill_reuters_sitemap_metadata(session, limit: int | None = None) -> dict:
    channel = session.query(Channel).filter(Channel.code == "reuters").first()
    if not channel:
        return {"processed_count": 0, "changed_count": 0, "status_counts": {}, "reason": "missing_reuters_channel"}

    query = (
        session.query(Info)
        .filter(
            Info.channel_id == channel.id,
            Info.is_deleted == 0,
            Info.detail_fetch_status.in_(("list_only", "pending", "failed", "")),
            Info.content.like("%official news sitemap%"),
            Info.content.like("%Official Reuters URL:%"),
        )
        .order_by(Info.event_time.desc(), Info.id.desc())
    )
    if limit:
        query = query.limit(limit)

    crawler = ReutersCrawler()
    status_counter: Counter[str] = Counter()
    processed_count = 0
    changed_count = 0
    for info in query.all():
        original = (
            info.detail_fetch_status or "",
            info.detail_strategy or "",
            info.detail_score or 0,
            info.detail_content_length or 0,
        )
        pipeline = crawler.resolve_detail(info.to_dict())
        info.content = pipeline.content or info.content
        info.detail_fetch_status = pipeline.status
        info.detail_fetch_error = pipeline.failure_reason
        info.detail_strategy = pipeline.strategy
        info.detail_score = pipeline.score
        info.detail_content_length = pipeline.content_length
        info.detail_fetched_at = datetime.now()
        _apply_info_semantics(info, info.content or "")
        _record_info_acquisition_log(
            session,
            info=info,
            channel_code="reuters",
            strategy=pipeline.strategy,
            status=pipeline.status,
            score=pipeline.score,
            content_length=pipeline.content_length,
            failure_reason=pipeline.failure_reason,
            matched_rules=pipeline.matched_rules,
            content=info.content or "",
        )
        processed_count += 1
        status_counter[pipeline.status] += 1
        changed_count += int(
            original
            != (
                info.detail_fetch_status or "",
                info.detail_strategy or "",
                info.detail_score or 0,
                info.detail_content_length or 0,
            )
        )

    session.commit()
    return {
        "processed_count": processed_count,
        "changed_count": changed_count,
        "status_counts": dict(sorted(status_counter.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill persisted Reuters sitemap metadata detail quality.")
    parser.add_argument("--limit", type=int, default=0, help="Limit processed rows. Default: all eligible rows.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    with get_session() as session:
        result = backfill_reuters_sitemap_metadata(session, limit=args.limit or None)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()

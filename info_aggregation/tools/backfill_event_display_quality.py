import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import get_session
from services.analysis.event_display_quality import backfill_event_display_quality


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill event display quality fields and statuses.")
    parser.add_argument("--limit", type=int, default=0, help="Limit processed events. Default: all eligible events.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    session = get_session()
    try:
        result = backfill_event_display_quality(session, limit=args.limit or None)
    finally:
        session.close()

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()

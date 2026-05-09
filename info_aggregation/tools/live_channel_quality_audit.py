"""
本地真实采集样本验收工具。

用法：
    python tools/live_channel_quality_audit.py --channels weibo,zhihu --limit 3

这个工具只读线上渠道，不写数据库。它用于开发阶段快速判断：
1. 热点入口是否能返回真实线上数据；
2. 详情二次抓取是否完整；
3. 失败原因是 Cookie 缺失、反爬、空壳页，还是内容本身过短。
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crawlers.registry import crawler_registry  # noqa: E402
from main import register_all_crawlers, setup_logging  # noqa: E402
from services.collection.credential_provider import build_credential_report  # noqa: E402


def audit_channels(channel_codes: list[str], limit: int = 3, fetch_detail: bool = True) -> dict:
    if not crawler_registry.list_channels():
        register_all_crawlers()

    results = []
    for channel_code in channel_codes:
        crawler = crawler_registry.get(channel_code)
        if not crawler:
            results.append(
                {
                    "channel_code": channel_code,
                    "status": "failed",
                    "error": "crawler_not_registered",
                    "items": [],
                }
            )
            continue

        channel_result = {
            "channel_code": channel_code,
            "channel_name": crawler.channel_name,
            "status": "success",
            "error": "",
            "credential_health": build_credential_report([channel_code]).get(channel_code, {}),
            "raw_count": 0,
            "items": [],
        }
        try:
            with crawler_registry.get_lock(channel_code):
                items = crawler.safe_crawl()
            channel_result["raw_count"] = len(items)
            for item in items[:limit]:
                item_result = {
                    "title": item.get("title", ""),
                    "source_url": item.get("source_url", ""),
                    "list_content_length": len(item.get("content", "") or ""),
                }
                if fetch_detail:
                    with crawler_registry.get_lock(channel_code):
                        _, _, _, detail = crawler.safe_fetch_detail(item.get("source_url", ""), item)
                    item_result.update(
                        {
                            "detail_status": detail.status,
                            "detail_strategy": detail.strategy,
                            "detail_score": detail.score,
                            "detail_content_length": detail.content_length,
                            "failure_reason": detail.failure_reason,
                            "content_excerpt": (detail.content or item.get("content", "") or "")[:240],
                        }
                    )
                channel_result["items"].append(item_result)
        except Exception as exc:
            channel_result["status"] = "failed"
            channel_result["error"] = str(exc)
        results.append(channel_result)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "limit": limit,
        "fetch_detail": fetch_detail,
        "channels": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="本地真实采集样本验收工具")
    parser.add_argument(
        "--channels",
        default="weibo,toutiao,zhihu,xiaohongshu,36kr,reuters",
        help="逗号分隔的渠道编码，例如 weibo,zhihu,toutiao",
    )
    parser.add_argument("--limit", type=int, default=3, help="每个渠道抽取的样本数量")
    parser.add_argument("--skip-detail", action="store_true", help="只检查热点入口，不抓详情")
    return parser.parse_args()


def main():
    setup_logging()
    args = _parse_args()
    channel_codes = [channel.strip() for channel in args.channels.split(",") if channel.strip()]
    report = audit_channels(channel_codes, limit=max(1, args.limit), fetch_detail=not args.skip_detail)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

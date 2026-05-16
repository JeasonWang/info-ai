#!/usr/bin/env bash
set -euo pipefail

# 真实数据轻量验收脚本。
# 默认只读接口，不触发采集、重建、归档等写库动作。

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGGREGATION_BASE_URL="${AGGREGATION_BASE_URL:-http://127.0.0.1:8000}"
INFO_SERVE_BASE_URL="${INFO_SERVE_BASE_URL:-http://127.0.0.1:8085}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/logs/local/acceptance}"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
RUN_DIR="$OUTPUT_DIR/$TIMESTAMP"

mkdir -p "$RUN_DIR"

python3 - "$AGGREGATION_BASE_URL" "$INFO_SERVE_BASE_URL" "$RUN_DIR" <<'PY'
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

aggregation_base, serve_base, run_dir = sys.argv[1:]
run_path = Path(run_dir)


def fetch_json(name: str, url: str) -> dict:
    target = run_path / f"{name}.json"
    try:
        with urlopen(url, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        data = {"ok": False, "error": str(exc), "url": url}
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def unwrap(payload: dict):
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


health_aggregation = fetch_json("aggregation-health", f"{aggregation_base}/health")
health_serve = fetch_json("info-serve-health", f"{serve_base}/health")
channel_quality = unwrap(fetch_json("channel-quality-report", f"{aggregation_base}/api/admin/channel-quality-report?sample_limit=3"))
event_quality = unwrap(fetch_json("event-analysis-quality-report", f"{aggregation_base}/api/admin/event-analysis-quality-report?limit=10"))
events_list = unwrap(fetch_json("events-list", f"{serve_base}/api/v1/events?page=1&page_size=20"))

items = []
if isinstance(events_list, dict):
    items = events_list.get("items") or []

detail = {}
if items:
    event_id = items[0].get("id")
    detail = unwrap(fetch_json("event-detail", f"{serve_base}/api/v1/events/{event_id}"))
else:
    (run_path / "event-detail.json").write_text("{}", encoding="utf-8")


def line(text: str = ""):
    report_lines.append(text)


def fmt_ratio(value):
    return f"{value}%" if value is not None else "-"


def clipped(text: str, limit: int = 72) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "..."


channel_summary = channel_quality.get("summary", {}) if isinstance(channel_quality, dict) else {}
core_sources = channel_quality.get("core_sources", []) if isinstance(channel_quality, dict) else []
event_summary = event_quality.get("summary", {}) if isinstance(event_quality, dict) else {}
risk_events = event_quality.get("risk_events", []) if isinstance(event_quality, dict) else []
display_quality = event_quality.get("display_quality", {}) if isinstance(event_quality, dict) else {}
display_summary = display_quality.get("summary", {}) if isinstance(display_quality, dict) else {}
blocked_samples = display_quality.get("blocked_samples", []) if isinstance(display_quality, dict) else []

bad_summary_markers = ("Reuters category:", "Official Reuters URL:", "Published at", "  ", "相关讨论正在升温")
suspect_cards = [
    item for item in items
    if any(marker in (item.get("one_line_summary") or "") for marker in bad_summary_markers)
    or len(item.get("one_line_summary") or "") < 18
]

report_lines: list[str] = []
line("# 信息达人本地验收快照")
line()
line(f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
line(f"- 采集服务：{aggregation_base}")
line(f"- 业务服务：{serve_base}")
line()
line("## 服务健康")
line()
line(f"- info_aggregation：{health_aggregation.get('message', health_aggregation.get('error', 'unknown'))}")
line(f"- info-serve：{health_serve.get('message', health_serve.get('error', 'unknown'))}")
line()
line("## 采集质量")
line()
line(f"- 真实内容：{channel_summary.get('real_count', 0)}")
line(f"- 完整率：{fmt_ratio(channel_summary.get('complete_ratio'))}")
line(f"- 可用率：{fmt_ratio(channel_summary.get('usable_ratio'))}")
line(f"- 待治理：{channel_summary.get('needs_attention_count', 0)} / {fmt_ratio(channel_summary.get('needs_attention_ratio'))}")
line()
line("| 核心信源 | 可用率 | 主要问题 | 下一步 |")
line("|---|---:|---|---|")
for item in core_sources:
    line(
        f"| {item.get('channel_name', item.get('channel_code', '-'))} | "
        f"{fmt_ratio(item.get('usable_ratio'))} | "
        f"{item.get('primary_issue', '-')} | {item.get('next_action', '-')} |"
    )
line()
line("## 事件分析与展示质量")
line()
line(f"- 活跃事件：{event_summary.get('active_event_count', 0)}")
line(f"- 风险事件：{event_summary.get('risk_event_count', 0)}")
line(f"- 低置信度：{event_summary.get('low_confidence_count', 0)}")
line(f"- 模型回退：{event_summary.get('fallback_count', 0)}")
line(f"- 展示可用率：{fmt_ratio(display_summary.get('display_ready_ratio'))}")
line(f"- 展示拦截：{display_summary.get('blocked_count', 0)}")
line()
line("| 风险事件 | 主要问题 | 下一步 |")
line("|---|---|---|")
for item in risk_events[:5]:
    line(f"| {clipped(item.get('title'))} | {item.get('primary_issue', '-')} | {item.get('next_action', '-')} |")
line()
line("| 展示拦截样本 | 主要问题 | 下一步 |")
line("|---|---|---|")
for item in blocked_samples[:5]:
    line(f"| {clipped(item.get('title'))} | {item.get('primary_issue', '-')} | {item.get('next_action', '-')} |")
line()
line("## 用户端事件接口")
line()
line(f"- 事件总数：{events_list.get('total', 0) if isinstance(events_list, dict) else 0}")
line(f"- 首页抽样：{len(items)} 条")
line(f"- 疑似摘要问题：{len(suspect_cards)} 条")
line()
line("| 事件 | 摘要 | 质量 |")
line("|---|---|---:|")
for item in items[:8]:
    line(
        f"| {clipped(item.get('title'))} | "
        f"{clipped(item.get('one_line_summary'))} | "
        f"{item.get('display_quality_score', 0)} |"
    )
line()
if detail:
    line("## 详情页结构抽检")
    line()
    line(f"- 事件 ID：{detail.get('event', {}).get('id') or detail.get('id') or items[0].get('id')}")
    line(f"- 情报判断：{'有' if detail.get('intelligence_brief') else '缺'}")
    line(f"- 证据链：{'有' if detail.get('evidence_chain') else '缺'}")
    line(f"- 争议提示：{'有' if detail.get('controversy_brief') else '缺'}")
    line(f"- 多源视角：{len(detail.get('source_views') or [])} 条")
    line(f"- 历史关联：{len(detail.get('related_events') or [])} 条")
line()
line("## 输出文件")
line()
for path in sorted(run_path.glob("*.json")):
    line(f"- `{path.name}`")

(run_path / "summary.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
print(run_path / "summary.md")
PY

echo
echo "验收快照已生成：$RUN_DIR/summary.md"

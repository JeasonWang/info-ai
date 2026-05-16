from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from services.collection.detail_pipeline import DetailPipelineResult, DetailStrategyResult, run_detail_pipeline
from services.collection.html_article_extractor import HtmlArticleExtractor


@dataclass
class DetailReplayCase:
    name: str
    channel_code: str
    title: str
    list_content: str
    source_path: Path
    source_format: str
    expected_terms: list[str]
    forbidden_terms: list[str]


def load_replay_cases(manifest_path: Path) -> list[DetailReplayCase]:
    """读取详情回放样本清单，路径相对 manifest 所在目录解析。"""

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: list[DetailReplayCase] = []
    for item in payload["cases"]:
        cases.append(
            DetailReplayCase(
                name=item["name"],
                channel_code=item["channel_code"],
                title=item["title"],
                list_content=item.get("list_content", item["title"]),
                source_path=manifest_path.parent / item["source_file"],
                source_format=item["source_format"],
                expected_terms=item.get("expected_terms", []),
                forbidden_terms=item.get("forbidden_terms", []),
            )
        )
    return cases


def run_replay_case(case: DetailReplayCase) -> DetailPipelineResult:
    """执行单个详情样本回放，并复用正式 detail_pipeline 做质量判断。"""

    if case.source_format == "html":
        content = HtmlArticleExtractor().extract(case.source_path.read_text(encoding="utf-8"))
        strategy = "replay_html_article"
    elif case.source_format == "json":
        content = _extract_json_text(json.loads(case.source_path.read_text(encoding="utf-8")))
        strategy = "replay_json_text"
    else:
        content = ""
        strategy = "replay_unknown"

    return run_detail_pipeline(
        title=case.title,
        list_content=case.list_content,
        strategy_results=[DetailStrategyResult(strategy=strategy, content=content)],
    )


def _extract_json_text(value: Any) -> str:
    text_parts: list[str] = []
    interesting_keys = {
        "text",
        "longTextContent",
        "content",
        "summary",
        "note",
        "raw_text",
        "desc",
    }

    def walk(node: Any, key: str = ""):
        if isinstance(node, dict):
            for child_key, child_value in node.items():
                walk(child_value, child_key)
            return
        if isinstance(node, list):
            for child in node:
                walk(child, key)
            return
        if isinstance(node, str) and key in interesting_keys:
            cleaned = " ".join(node.split()).strip()
            if cleaned and cleaned not in text_parts:
                text_parts.append(cleaned)

    walk(value)
    return " ".join(text_parts)

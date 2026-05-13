from .schemas import EventAnalysisResult
from .text_utils import clean_source_text, ensure_sentence_end, text_similarity
from services.quality.data_quality import is_low_value_content


SUMMARY_FIELDS = [
    "one_line_summary",
    "what_happened",
    "why_it_matters",
    "latest_update",
    "heat_reason",
    "risk_notice",
    "source_compare",
    "analysis_confidence",
]


def normalize_result(result: EventAnalysisResult, title: str = "") -> EventAnalysisResult:
    for field_name in SUMMARY_FIELDS:
        value = clean_source_text(getattr(result, field_name, ""))
        setattr(result, field_name, ensure_sentence_end(value))
    for point in result.timeline_points:
        point.summary = ensure_sentence_end(clean_source_text(point.summary))
    if title and text_similarity(result.one_line_summary, title) >= 0.9:
        result.one_line_summary = ensure_sentence_end(f"{title}正在形成热点讨论，后续进展值得持续跟踪")
    return result


def validate_result(result: EventAnalysisResult) -> list[str]:
    problems: list[str] = []
    for field_name in SUMMARY_FIELDS:
        value = getattr(result, field_name, "")
        if len(value) < 8:
            problems.append(f"{field_name}_too_short")
        if value.endswith(("，", "、", "；", "：", ",")):
            problems.append(f"{field_name}_broken_sentence")
        if field_name != "analysis_confidence" and is_low_value_content("", value):
            problems.append(f"{field_name}_low_value")
    if result.what_happened == result.one_line_summary:
        problems.append("what_happened_duplicates_one_line")
    if not result.timeline_points:
        problems.append("missing_timeline")
    return problems

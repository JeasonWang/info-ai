from dataclasses import dataclass

from database import Info
from services.quality.data_quality import is_title_content_duplicate, is_unusable_detail_content, normalize_text
from services.collection.detail_pipeline import get_channel_detail_profile


ARTICLE_CONTENT_TYPES = {"article", "qa", "sports_news", "finance_indicator"}
OPEN_DETAIL_STATUSES = {"pending", "failed", "list_only", ""}


@dataclass(frozen=True)
class AcquisitionQualityProfile:
    channel_code: str
    content_type: str
    status: str
    quality_level: str
    usable: bool
    needs_attention: bool
    should_enqueue_detail_job: bool
    detail_score: int
    content_length: int
    required_length: int
    completeness_score: int
    value_score: int
    freshness_score: int
    attention_priority: int
    risk_reasons: list[str]
    recommended_action: str
    summary: str


def build_acquisition_quality_profile(info: Info) -> AcquisitionQualityProfile:
    """统一评估采集结果质量，供补偿队列、质量报告和事件构建复用。"""

    channel_code = info.channel.code if info.channel else ""
    detail_profile = get_channel_detail_profile(channel_code)
    content = info.content or ""
    normalized_content = normalize_text(content)
    content_length = info.detail_content_length or len(normalized_content)
    detail_status = (info.detail_fetch_status or "").strip()
    detail_score = info.detail_score or 0
    required_length = detail_profile.complete_min_length
    risk_reasons = _risk_reasons(info, normalized_content, content_length, required_length)
    completeness_score = _completeness_score(detail_status, detail_score, content_length, required_length, risk_reasons)
    value_score = _value_score(info, normalized_content, detail_profile.value_markers, risk_reasons)
    freshness_score = 80 if info.event_time else 50
    quality_level = _quality_level(completeness_score, value_score, risk_reasons)
    usable = quality_level in {"excellent", "usable"}
    needs_attention = quality_level in {"weak", "unusable"}
    should_enqueue = needs_attention and "seed_data" not in risk_reasons
    recommended_action = _recommended_action(risk_reasons, detail_profile.content_type)

    return AcquisitionQualityProfile(
        channel_code=channel_code,
        content_type=detail_profile.content_type,
        status=detail_status,
        quality_level=quality_level,
        usable=usable,
        needs_attention=needs_attention,
        should_enqueue_detail_job=should_enqueue,
        detail_score=detail_score,
        content_length=content_length,
        required_length=required_length,
        completeness_score=completeness_score,
        value_score=value_score,
        freshness_score=freshness_score,
        attention_priority=_attention_priority(risk_reasons, recommended_action, quality_level),
        risk_reasons=risk_reasons,
        recommended_action=recommended_action,
        summary=_quality_summary(quality_level, risk_reasons, recommended_action),
    )


def quality_profile_to_dict(profile: AcquisitionQualityProfile) -> dict:
    return {
        "channel_code": profile.channel_code,
        "content_type": profile.content_type,
        "status": profile.status,
        "quality_level": profile.quality_level,
        "usable": profile.usable,
        "needs_attention": profile.needs_attention,
        "should_enqueue_detail_job": profile.should_enqueue_detail_job,
        "detail_score": profile.detail_score,
        "content_length": profile.content_length,
        "required_length": profile.required_length,
        "completeness_score": profile.completeness_score,
        "value_score": profile.value_score,
        "freshness_score": profile.freshness_score,
        "attention_priority": profile.attention_priority,
        "risk_reasons": profile.risk_reasons,
        "recommended_action": profile.recommended_action,
        "summary": profile.summary,
    }


def _risk_reasons(info: Info, normalized_content: str, content_length: int, required_length: int) -> list[str]:
    reasons: list[str] = []
    detail_status = (info.detail_fetch_status or "").strip()
    detail_error = (info.detail_fetch_error or "").strip()
    detail_strategy = (info.detail_strategy or "").strip().lower()

    if detail_strategy == "seed":
        reasons.append("seed_data")
    if detail_status in OPEN_DETAIL_STATUSES:
        reasons.append(f"detail_{detail_status or 'unknown'}")
    if is_unusable_detail_content(info.content or "") or detail_error in {"anti_crawl_blocked", "shell_page"}:
        reasons.append("anti_crawl_or_shell_page")
    if not normalized_content:
        reasons.append("empty_content")
    elif is_title_content_duplicate(info.title or "", normalized_content):
        reasons.append("title_only_content")
    if content_length < required_length:
        reasons.append("below_channel_required_length")
    if (info.detail_score or 0) < 60:
        reasons.append("low_detail_score")
    if detail_status == "partial":
        reasons.append("partial_detail")

    return list(dict.fromkeys(reasons))


def _completeness_score(
    detail_status: str,
    detail_score: int,
    content_length: int,
    required_length: int,
    risk_reasons: list[str],
) -> int:
    if "seed_data" in risk_reasons:
        return 0
    if "empty_content" in risk_reasons or "anti_crawl_or_shell_page" in risk_reasons:
        return 0
    status_bonus = {
        "complete": 45,
        "partial": 25,
        "list_only": 8,
        "pending": 5,
        "failed": 0,
    }.get(detail_status, 5)
    length_score = min(35, int(content_length * 35 / max(required_length, 1)))
    score_part = min(20, int(detail_score / 5))
    penalty = 20 if "title_only_content" in risk_reasons else 0
    return max(0, min(100, status_bonus + length_score + score_part - penalty))


def _value_score(info: Info, normalized_content: str, markers: tuple[str, ...], risk_reasons: list[str]) -> int:
    if "seed_data" in risk_reasons or "empty_content" in risk_reasons:
        return 0
    score = 35
    if info.tech_entities:
        score += 15
    if info.tech_keywords:
        score += 15
    if markers and any(marker.lower() in normalized_content for marker in markers):
        score += 15
    if len(normalized_content) >= 160:
        score += 10
    if "title_only_content" in risk_reasons:
        score -= 30
    return max(0, min(score, 100))


def _quality_level(completeness_score: int, value_score: int, risk_reasons: list[str]) -> str:
    if "seed_data" in risk_reasons or "empty_content" in risk_reasons or "anti_crawl_or_shell_page" in risk_reasons:
        return "unusable"
    if completeness_score >= 80 and value_score >= 60:
        return "excellent"
    if completeness_score >= 65 and value_score >= 45:
        return "usable"
    if completeness_score >= 35 or value_score >= 35:
        return "weak"
    return "unusable"


def _recommended_action(risk_reasons: list[str], content_type: str) -> str:
    if "seed_data" in risk_reasons:
        return "exclude_from_quality_report"
    if "anti_crawl_or_shell_page" in risk_reasons:
        return "check_cookie_or_rendering_strategy"
    if "empty_content" in risk_reasons:
        return "retry_detail_fetch"
    if "below_channel_required_length" in risk_reasons and content_type in ARTICLE_CONTENT_TYPES:
        return "retry_full_article_detail"
    if "partial_detail" in risk_reasons:
        return "retry_with_channel_specific_strategy"
    if "title_only_content" in risk_reasons:
        return "search_secondary_detail_source"
    if "low_detail_score" in risk_reasons:
        return "retry_detail_quality_pipeline"
    return "keep_monitoring"


def _attention_priority(risk_reasons: list[str], recommended_action: str, quality_level: str) -> int:
    if "seed_data" in risk_reasons or quality_level in {"excellent", "usable"}:
        return 0
    if "anti_crawl_or_shell_page" in risk_reasons:
        return 95
    if "empty_content" in risk_reasons:
        return 90
    if "detail_failed" in risk_reasons:
        return 88
    if "detail_list_only" in risk_reasons:
        return 84
    if recommended_action == "retry_full_article_detail":
        return 76
    if recommended_action == "search_secondary_detail_source":
        return 72
    if "low_detail_score" in risk_reasons:
        return 68
    return 50


def _quality_summary(quality_level: str, risk_reasons: list[str], recommended_action: str) -> str:
    if quality_level == "excellent":
        return "详情完整度高，可作为事件分析的核心来源。"
    if quality_level == "usable":
        return "详情可用，但仍建议继续观察更多来源。"
    if "anti_crawl_or_shell_page" in risk_reasons:
        return "疑似登录、反爬或壳页面，需要检查 Cookie 或渲染策略。"
    if "empty_content" in risk_reasons:
        return "正文为空，需要重新抓取详情。"
    if "detail_list_only" in risk_reasons:
        return "当前仍是列表摘要，需要二次抓取详情页。"
    if recommended_action == "retry_full_article_detail":
        return "正文短于渠道完整标准，需要重抓完整文章。"
    return "详情质量偏弱，需要进入补偿队列继续提升。"

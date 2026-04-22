from dataclasses import dataclass, field
import re


INVALID_PATTERNS = {
    "shell_page": [
        "你访问的页面不见了",
        "沪ICP备",
        "营业执照",
        "增值电信业务经营许可证",
        "行吟信息科技",
        "随时随地发现新鲜事",
        "超话社区",
        "热门微博",
        "登录 注册",
        "您需要允许该网站执行 JavaScript",
        "需要允许该网站执行 JavaScript",
    ],
    "anti_crawl_blocked": [
        "请先登录",
        "异常访问",
        "访问频次过高",
        "验证后继续访问",
        "登录注册更精彩",
    ],
}

TITLE_NOISE_WORDS = {
    "发布",
    "宣布",
    "回应",
    "通报",
    "热搜",
    "微博",
    "突发",
    "曝光",
    "上线",
}


@dataclass
class DetailStrategyResult:
    strategy: str
    content: str
    failure_reason: str = ""
    matched_rules: list[str] = field(default_factory=list)


@dataclass
class DetailPipelineResult:
    content: str
    status: str
    strategy: str
    score: int
    content_length: int
    failure_reason: str
    matched_rules: list[str]


def normalize_content(content: str) -> str:
    text = content or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_meaningful_markers(title: str) -> list[str]:
    """
    从标题里提取更稳定的关键词标记，减少中文标题或中英混合标题被误判为弱相关。
    """
    normalized_title = re.sub(r"\s+", "", title or "")
    if not normalized_title:
        return []

    markers: list[str] = []
    seen: set[str] = set()

    def add_marker(marker: str):
        cleaned_marker = marker.strip()
        if len(cleaned_marker) < 2 or cleaned_marker in TITLE_NOISE_WORDS or cleaned_marker in seen:
            return
        markers.append(cleaned_marker)
        seen.add(cleaned_marker)

    if len(normalized_title) >= 4:
        add_marker(normalized_title[:4])
    else:
        add_marker(normalized_title)

    # 保留原始标题里的英文词和数字词，兼容 “AI Agent”“OpenAI API” 这类带空格标题。
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", title or ""):
        add_marker(token)

    # 优先保留英文/数字混合词，例如 OpenAI、H200，避免只靠中文前缀做判断。
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", normalized_title):
        add_marker(token)

    # 将中文标题按常见动作词切开，保留更像主体或对象的片段，例如“英伟达”“芯片”。
    chinese_segments = re.split(r"(?:发布|宣布|回应|通报|上线|曝光|热搜|微博|突发)", normalized_title)
    for segment in chinese_segments:
        cleaned_segment = re.sub(r"[^一-\u9fff]", "", segment)
        if len(cleaned_segment) >= 2:
            add_marker(cleaned_segment)
            if len(cleaned_segment) > 4:
                add_marker(cleaned_segment[-4:])

    return markers


def validate_content(title: str, content: str) -> tuple[str, str, list[str]]:
    if not content:
        return "failed", "empty_content", ["empty_content"]

    matched_rules: list[str] = []
    for reason in ("anti_crawl_blocked", "shell_page"):
        patterns = INVALID_PATTERNS[reason]
        if any(pattern in content for pattern in patterns):
            matched_rules.append(reason)
            return "failed", reason, matched_rules

    if len(content) < 20:
        matched_rules.append("content_too_short")
        return "failed", "content_too_short", matched_rules

    meaningful_markers = extract_meaningful_markers(title)
    if meaningful_markers and not any(marker and marker in content for marker in meaningful_markers):
        matched_rules.append("weak_relevance")
        return "partial", "weak_relevance", matched_rules

    if len(content) < 40:
        matched_rules.append("partial_content")
        return "partial", "content_too_short", matched_rules

    return "complete", "", matched_rules


def score_content(title: str, content: str, matched_rules: list[str]) -> int:
    if not content:
        return 0
    score = 60 + min(len(content) // 2, 30)
    if "shell_page" in matched_rules or "anti_crawl_blocked" in matched_rules:
        return 0
    if "weak_relevance" in matched_rules:
        score -= 35
    if "partial_content" in matched_rules:
        score -= 20
    if title and title in content:
        score += 10
    return max(0, min(score, 100))


def run_detail_pipeline(title: str, list_content: str, strategy_results: list[DetailStrategyResult]) -> DetailPipelineResult:
    last_failed = DetailPipelineResult(
        content="",
        status="failed",
        strategy="",
        score=0,
        content_length=0,
        failure_reason="detail_unavailable",
        matched_rules=[],
    )
    best_partial: DetailPipelineResult | None = None
    anti_crawl_failed: DetailPipelineResult | None = None

    for candidate in strategy_results:
        normalized = normalize_content(candidate.content)
        status, reason, matched_rules = validate_content(title, normalized)
        score = score_content(title, normalized, matched_rules)
        result = DetailPipelineResult(
            content=normalized,
            status=status,
            strategy=candidate.strategy,
            score=score,
            content_length=len(normalized),
            failure_reason=reason,
            matched_rules=matched_rules,
        )
        if status == "complete":
            return result
        if status == "partial":
            if best_partial is None or result.score > best_partial.score:
                best_partial = result
            continue
        if result.failure_reason == "anti_crawl_blocked":
            anti_crawl_failed = result
        last_failed = result

    if best_partial is not None:
        return best_partial

    if anti_crawl_failed is not None:
        return anti_crawl_failed

    fallback = normalize_content(list_content)
    normalized_title = normalize_content(title)
    if fallback and fallback != normalized_title:
        return DetailPipelineResult(
            content=fallback,
            status="list_only",
            strategy="list_fallback",
            score=10,
            content_length=len(fallback),
            failure_reason="detail_unavailable",
            matched_rules=[],
        )
    return last_failed

from dataclasses import dataclass, field
import re


FULL_CONTENT_MAX_LENGTH = 12000


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
        "{{ model_title.title }}",
        "{{ item.user_name }}",
        "快速概览(Qwen3",
        "深度思考(DS-R1",
        "问题分析中",
        "答案整理中",
        "sec_sdk_build",
        "captchaOptions",
        "滑块验证",
        "登录后推荐更懂你的笔记",
        "我已阅读并同意《用户协议》《隐私政策》",
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


@dataclass(frozen=True)
class ChannelDetailProfile:
    channel_code: str
    content_type: str
    complete_min_length: int
    partial_min_length: int
    strong_complete_min_length: int
    require_title_relevance: bool = True
    paragraph_min_count: int = 1
    value_markers: tuple[str, ...] = ()


@dataclass
class DetailPipelineResult:
    content: str
    status: str
    strategy: str
    score: int
    content_length: int
    failure_reason: str
    matched_rules: list[str]


DEFAULT_DETAIL_PROFILE = ChannelDetailProfile(
    channel_code="default",
    content_type="hot_topic",
    complete_min_length=40,
    partial_min_length=20,
    strong_complete_min_length=120,
)


CHANNEL_DETAIL_PROFILES = {
    "weibo": ChannelDetailProfile("weibo", "hot_topic", 80, 30, 180, value_markers=("热搜", "话题", "回应", "通报", "讨论")),
    "toutiao": ChannelDetailProfile("toutiao", "hot_topic", 45, 35, 180, value_markers=("热点", "事件", "回应", "通报", "原因", "数据", "交通", "出行", "游客", "比赛", "小组赛", "选手", "冠军", "夺冠", "去世", "影响", "提醒", "媒体", "价格", "消费", "市场", "旅游", "退款", "彩礼", "婚姻", "政策")),
    "zhihu": ChannelDetailProfile("zhihu", "qa", 150, 20, 600, value_markers=("回答", "问题", "观点", "认为", "讨论", "如何", "解读", "报告", "数据", "同比", "分析", "影响", "事件")),
    "xiaohongshu": ChannelDetailProfile("xiaohongshu", "social_note", 120, 20, 260, value_markers=("笔记", "体验", "分享", "建议")),
    "cnblogs": ChannelDetailProfile("cnblogs", "article", 500, 20, 1000, paragraph_min_count=2, value_markers=("代码", "实现", "架构", "配置", "问题", "方案")),
    "csdn": ChannelDetailProfile("csdn", "article", 600, 20, 1200, paragraph_min_count=2, value_markers=("代码", "实现", "配置", "报错", "解决", "方案")),
    "juejin": ChannelDetailProfile("juejin", "article", 600, 20, 1200, paragraph_min_count=2, value_markers=("前端", "后端", "源码", "实现", "性能", "工程", "代码", "程序员", "Cursor", "AI")),
    "36kr": ChannelDetailProfile("36kr", "article", 500, 20, 1000, paragraph_min_count=2, value_markers=("公司", "融资", "产品", "市场", "商业", "AI")),
    "reuters": ChannelDetailProfile("reuters", "article", 500, 20, 1000, paragraph_min_count=2, value_markers=("said", "according", "government", "market", "official", "company")),
    "eastmoney": ChannelDetailProfile("eastmoney", "finance_indicator", 160, 70, 320, value_markers=("上涨", "下跌", "市场", "投资者", "走势", "政策", "美元", "汇率", "金价", "原油")),
    "cctv_sports": ChannelDetailProfile("cctv_sports", "sports_news", 240, 40, 500, value_markers=("比赛", "赛事", "球队", "球员", "冠军", "比分", "赛季")),
    "sina_sports": ChannelDetailProfile("sina_sports", "sports_news", 240, 40, 500, value_markers=("比赛", "赛事", "球队", "球员", "冠军", "比分", "赛季")),
}


def get_channel_detail_profile(channel_code: str = "") -> ChannelDetailProfile:
    return CHANNEL_DETAIL_PROFILES.get((channel_code or "").strip(), DEFAULT_DETAIL_PROFILE)


def normalize_content(content: str) -> str:
    text = content or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def limit_detail_content(content: str, max_length: int = FULL_CONTENT_MAX_LENGTH) -> str:
    """限制异常超长正文，正常文章不再按摘要长度截断。"""

    if not content:
        return ""
    return content[:max_length]


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


def _paragraph_count(content: str) -> int:
    return len([part for part in re.split(r"(?:。|！|？|\.|\n)+", content or "") if len(part.strip()) >= 20])


def _has_value_marker(content: str, profile: ChannelDetailProfile) -> bool:
    if not profile.value_markers:
        return True
    normalized = (content or "").lower()
    return any(marker.lower() in normalized for marker in profile.value_markers)


def validate_content(title: str, content: str, profile: ChannelDetailProfile | None = None) -> tuple[str, str, list[str]]:
    profile = profile or DEFAULT_DETAIL_PROFILE
    if not content:
        return "failed", "empty_content", ["empty_content"]

    matched_rules: list[str] = []
    for reason in ("anti_crawl_blocked", "shell_page"):
        patterns = INVALID_PATTERNS[reason]
        if any(pattern in content for pattern in patterns):
            matched_rules.append(reason)
            return "failed", reason, matched_rules

    if len(content) < profile.partial_min_length:
        matched_rules.append("content_too_short")
        return "failed", "content_too_short", matched_rules

    meaningful_markers = extract_meaningful_markers(title)
    if profile.require_title_relevance and meaningful_markers and not any(marker and marker in content for marker in meaningful_markers):
        matched_rules.append("weak_relevance")
        return "partial", "weak_relevance", matched_rules

    if len(content) < profile.complete_min_length:
        matched_rules.append("below_channel_complete_threshold")
        return "partial", "content_below_channel_complete_threshold", matched_rules

    if profile.paragraph_min_count > 1 and _paragraph_count(content) < profile.paragraph_min_count:
        matched_rules.append("insufficient_paragraphs")
        return "partial", "insufficient_paragraphs", matched_rules

    if not _has_value_marker(content, profile):
        matched_rules.append("low_channel_value_density")
        return "partial", "low_channel_value_density", matched_rules

    return "complete", "", matched_rules


def score_content(title: str, content: str, matched_rules: list[str], profile: ChannelDetailProfile | None = None) -> int:
    profile = profile or DEFAULT_DETAIL_PROFILE
    if not content:
        return 0
    score = 55 + min(int((len(content) / max(profile.complete_min_length, 1)) * 25), 35)
    if "shell_page" in matched_rules or "anti_crawl_blocked" in matched_rules:
        return 0
    if "weak_relevance" in matched_rules:
        score -= 35
    if "below_channel_complete_threshold" in matched_rules:
        score -= 20
    if "insufficient_paragraphs" in matched_rules:
        score -= 15
    if "low_channel_value_density" in matched_rules:
        score -= 15
    if title and title in content:
        score += 10
    if len(content) >= profile.strong_complete_min_length:
        score += 8
    return max(0, min(score, 100))


def run_detail_pipeline(
    title: str,
    list_content: str,
    strategy_results: list[DetailStrategyResult],
    channel_code: str = "",
) -> DetailPipelineResult:
    profile = get_channel_detail_profile(channel_code)
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
        status, reason, matched_rules = validate_content(title, normalized, profile)
        if status == "failed" and candidate.failure_reason:
            reason = candidate.failure_reason
        matched_rules = list(dict.fromkeys([*candidate.matched_rules, *matched_rules]))
        score = score_content(title, normalized, matched_rules, profile)
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
            failure_reason=last_failed.failure_reason or "detail_unavailable",
            matched_rules=last_failed.matched_rules,
        )
    return last_failed

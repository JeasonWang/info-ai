"""
体育渠道爬虫通用工具。

这里集中放置体育新闻链接抽取、正文清洗、时间推断等轻量能力，
避免央视体育和新浪体育各自重复实现同一套规则。
"""
import hashlib
import html
import re
from datetime import datetime
from urllib.parse import urljoin

from services.collection.detail_pipeline import limit_detail_content


SPORTS_SKIP_KEYWORDS = (
    "彩票",
    "大乐透",
    "双色球",
    "足彩",
    "竞彩",
    "任九",
    "头奖",
    "滚存",
    "大奖",
    "投注",
    "赔率",
    "中奖",
)


def clean_html_text(raw_value: str) -> str:
    """把 HTML 片段清洗为适合入库和展示的纯文本。"""
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw_value or "", flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_url(base_url: str, raw_url: str) -> str:
    """标准化链接，兼容 //domain/path 和相对路径。"""
    if not raw_url:
        return ""
    if raw_url.startswith("//"):
        return f"https:{raw_url}"
    return urljoin(base_url, raw_url)


def stable_source_id(channel_code: str, source_url: str) -> str:
    """用渠道和原始链接生成稳定 source_id，保障重复抓取不会重复入库。"""
    return hashlib.md5(f"{channel_code}_{source_url}".encode("utf-8")).hexdigest()[:16]


def infer_datetime_from_url(source_url: str) -> datetime:
    """优先从新闻 URL 中提取发布日期，失败时使用当前时间。"""
    match = re.search(r"/(20\d{2})[/-](\d{1,2})[/-](\d{1,2})/", source_url or "")
    if match:
        year, month, day = [int(part) for part in match.groups()]
        try:
            return datetime(year, month, day)
        except ValueError:
            pass
    return datetime.now()


def is_useful_sports_title(title: str) -> bool:
    """过滤明显不适合作为体育新闻事件的数据。"""
    normalized = clean_html_text(title)
    if len(normalized) < 8:
        return False
    return not any(keyword in normalized for keyword in SPORTS_SKIP_KEYWORDS)


def extract_article_text(html_text: str, patterns: list[str]) -> str:
    """按候选正文容器提取文章正文，失败时返回空字符串。"""
    for pattern in patterns:
        match = re.search(pattern, html_text or "", re.DOTALL | re.IGNORECASE)
        if not match:
            continue
        content = clean_html_text(match.group(1))
        if len(content) >= 40:
            return limit_detail_content(content)

    description = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html_text or "",
        re.IGNORECASE,
    )
    if description:
        content = clean_html_text(description.group(1))
        if len(content) >= 20:
            return limit_detail_content(content)

    return ""

import re
from html import unescape

from services.collection.detail_pipeline import DetailStrategyResult


class HtmlArticleExtractor:
    """轻量 HTML 正文抽取器，作为 Trafilatura 接入前的本地稳定兜底。"""

    CONTAINER_PATTERNS = (
        r"<article[^>]*>(.*?)</article>",
        r'<div[^>]*class="[^"]*(?:article|content|detail|post|body|main)[^"]*"[^>]*>(.*?)</div>',
        r"<main[^>]*>(.*?)</main>",
        r"<body[^>]*>(.*?)</body>",
    )

    def extract(self, html: str) -> str:
        if not html:
            return ""

        for pattern in self.CONTAINER_PATTERNS:
            match = re.search(pattern, html, flags=re.DOTALL | re.IGNORECASE)
            if not match:
                continue
            text = self._clean_html_fragment(match.group(1))
            if len(text) >= 20:
                return text

        return self._clean_html_fragment(html)

    def _clean_html_fragment(self, fragment: str) -> str:
        text = re.sub(r"<script[^>]*>.*?</script>", " ", fragment, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<(?:nav|footer|header|aside)[^>]*>.*?</(?:nav|footer|header|aside)>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"</(?:p|h1|h2|h3|li|div|section)>", "。", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"。+", "。", text)
        return text.strip(" 。\t\r\n")


class StaticHtmlArticleStrategy:
    """把已有 HTML 转为详情候选正文，适合样本回放和低成本 HTML 策略复用。"""

    def __init__(self, html: str, strategy_name: str = "html_article"):
        self.html = html
        self.name = strategy_name
        self.extractor = HtmlArticleExtractor()

    def fetch(self, context) -> DetailStrategyResult:
        return DetailStrategyResult(
            strategy=self.name,
            content=self.extractor.extract(self.html),
        )

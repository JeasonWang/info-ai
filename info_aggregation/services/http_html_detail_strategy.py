from collections.abc import Callable

import httpx

from services.detail_pipeline import DetailStrategyResult
from services.html_article_extractor import HtmlArticleExtractor


HtmlFetcher = Callable[[str], str]
HtmlExtractFunc = Callable[[str], str | None]


def default_httpx_fetcher(url: str) -> str:
    """使用 HTTPX 获取 HTML，作为低成本详情策略的默认网络层。"""

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


class HttpHtmlDetailStrategy:
    """通过 HTTP 获取详情页 HTML，并抽取正文作为候选详情。"""

    name = "http_html_article"

    def __init__(self, fetcher: HtmlFetcher | None = None, extractor: HtmlArticleExtractor | None = None):
        self.fetcher = fetcher or default_httpx_fetcher
        self.extractor = extractor or TrafilaturaArticleExtractor()

    def fetch(self, context) -> DetailStrategyResult:
        if not context.source_url:
            return DetailStrategyResult(
                strategy=self.name,
                content="",
                failure_reason="missing_source_url",
                matched_rules=["missing_source_url"],
            )
        try:
            html = self.fetcher(context.source_url)
        except Exception as exc:
            return DetailStrategyResult(
                strategy=self.name,
                content="",
                failure_reason=type(exc).__name__,
                matched_rules=["http_fetch_error"],
            )
        return DetailStrategyResult(
            strategy=self.name,
            content=self.extractor.extract(html),
        )


class TrafilaturaArticleExtractor:
    """优先使用 Trafilatura 抽正文，依赖不可用或抽取为空时回退到本地 HTML 抽取器。"""

    def __init__(self, extract_func: HtmlExtractFunc | None = None, fallback: HtmlArticleExtractor | None = None):
        self.extract_func = extract_func or self._load_trafilatura_extract()
        self.fallback = fallback or HtmlArticleExtractor()

    def extract(self, html: str) -> str:
        if not html:
            return ""
        if self.extract_func:
            try:
                content = self.extract_func(html) or ""
            except Exception:
                content = ""
            content = " ".join(content.split()).strip()
            if len(content) >= 20:
                return content
        return self.fallback.extract(html)

    def _load_trafilatura_extract(self) -> HtmlExtractFunc | None:
        try:
            import trafilatura
        except Exception:
            return None
        return lambda html: trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

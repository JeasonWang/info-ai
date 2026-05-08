from collections.abc import Callable
import html
import re
from urllib.parse import quote_plus, unquote, urlparse

import httpx

from services.detail_pipeline import DetailStrategyResult, limit_detail_content
from services.http_html_detail_strategy import HtmlFetcher, TrafilaturaArticleExtractor, default_httpx_fetcher


SearchFetcher = Callable[[str], str]


CHANNEL_SEARCH_DOMAINS = {
    "36kr": ("36kr.com",),
    "cnblogs": ("cnblogs.com",),
    "csdn": ("csdn.net", "blog.csdn.net"),
    "juejin": ("juejin.cn",),
    "toutiao": ("toutiao.com",),
    "zhihu": ("zhihu.com",),
    "xiaohongshu": ("xiaohongshu.com",),
    "weibo": ("weibo.com", "s.weibo.com"),
    "reuters": ("reuters.com",),
    "eastmoney": ("eastmoney.com",),
    "cctv_sports": ("sports.cctv.com",),
    "sina_sports": ("sports.sina.com.cn",),
}


def default_bing_search_fetcher(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    with httpx.Client(timeout=12.0, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


class SecondarySearchDetailStrategy:
    """搜索同渠道候选详情页，解决热词页、列表摘要和标题正文类低质数据。"""

    name = "secondary_search"

    def __init__(
        self,
        search_fetcher: SearchFetcher | None = None,
        article_fetcher: HtmlFetcher | None = None,
        extractor: TrafilaturaArticleExtractor | None = None,
        max_candidates: int = 3,
    ):
        self.search_fetcher = search_fetcher or default_bing_search_fetcher
        self.article_fetcher = article_fetcher or default_httpx_fetcher
        self.extractor = extractor or TrafilaturaArticleExtractor()
        self.max_candidates = max(1, max_candidates)

    def fetch(self, context) -> DetailStrategyResult:
        domains = self._domains_for_channel(context.channel_code)
        if not domains:
            return DetailStrategyResult(
                strategy=self.name,
                content="",
                failure_reason="missing_search_domain",
                matched_rules=["missing_search_domain"],
            )

        try:
            search_html = self.search_fetcher(self._build_search_url(context.title, domains[0]))
        except Exception as exc:
            return DetailStrategyResult(
                strategy=self.name,
                content="",
                failure_reason=type(exc).__name__,
                matched_rules=["secondary_search_error"],
            )

        source_url = context.source_url or ""
        candidates = self._extract_candidate_urls(search_html, domains, source_url)[: self.max_candidates]
        if not candidates:
            return DetailStrategyResult(
                strategy=self.name,
                content="",
                failure_reason="secondary_search_no_candidate",
                matched_rules=["secondary_search_no_candidate"],
            )

        failures: list[str] = []
        for candidate_url in candidates:
            try:
                article_html = self.article_fetcher(candidate_url)
            except Exception as exc:
                failures.append(type(exc).__name__)
                continue
            content = self.extractor.extract(article_html)
            if content:
                return DetailStrategyResult(
                    strategy=self.name,
                    content=limit_detail_content(content),
                    matched_rules=[f"secondary_search_url:{candidate_url}"],
                )

        return DetailStrategyResult(
            strategy=self.name,
            content="",
            failure_reason="secondary_search_empty_article",
            matched_rules=["secondary_search_empty_article", *failures[:3]],
        )

    def _domains_for_channel(self, channel_code: str) -> tuple[str, ...]:
        return CHANNEL_SEARCH_DOMAINS.get((channel_code or "").strip(), ())

    def _build_search_url(self, title: str, domain: str) -> str:
        query = quote_plus(f"site:{domain} {title}".strip())
        return f"https://www.bing.com/search?q={query}&setlang=zh-CN"

    def _extract_candidate_urls(self, search_html: str, domains: tuple[str, ...], source_url: str = "") -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        source_norm = self._normalize_url(source_url)

        for href in re.findall(r'href=["\']([^"\']+)["\']', search_html or "", flags=re.IGNORECASE):
            candidate = self._normalize_search_href(html.unescape(href))
            if not candidate or candidate in seen:
                continue
            if source_norm and self._normalize_url(candidate) == source_norm:
                continue
            if not self._is_supported_domain(candidate, domains):
                continue
            seen.add(candidate)
            urls.append(candidate)
        return urls

    def _normalize_search_href(self, href: str) -> str:
        if not href:
            return ""
        if href.startswith("/"):
            return ""
        if "bing.com/ck/a" in href:
            match = re.search(r"[?&]u=([^&]+)", href)
            if match:
                href = unquote(match.group(1))
                if href.startswith("a1"):
                    href = href[2:]
        href = unquote(href)
        if not href.startswith(("http://", "https://")):
            return ""
        return href.split("#", 1)[0]

    def _is_supported_domain(self, url: str, domains: tuple[str, ...]) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in domains)

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url or "")
        if not parsed.netloc:
            return ""
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc.lower()}{path}"


class ZhihuSecondarySearchDetailStrategy(SecondarySearchDetailStrategy):
    """知乎专用二跳搜索，优先定位问题、回答和专栏文章详情页。"""

    name = "zhihu_secondary_search"

    def _domains_for_channel(self, channel_code: str) -> tuple[str, ...]:
        return ("zhihu.com",)

    def _build_search_url(self, title: str, domain: str) -> str:
        query = quote_plus(f"site:zhihu.com/question OR site:zhuanlan.zhihu.com {title}".strip())
        return f"https://www.bing.com/search?q={query}&setlang=zh-CN"


class XiaohongshuSecondarySearchDetailStrategy(SecondarySearchDetailStrategy):
    """小红书专用二跳搜索，优先定位笔记详情页。"""

    name = "xiaohongshu_secondary_search"

    def _domains_for_channel(self, channel_code: str) -> tuple[str, ...]:
        return ("xiaohongshu.com",)

    def _build_search_url(self, title: str, domain: str) -> str:
        query = quote_plus(f"site:xiaohongshu.com/explore {title}".strip())
        return f"https://www.bing.com/search?q={query}&setlang=zh-CN"


class WeiboSecondarySearchDetailStrategy(SecondarySearchDetailStrategy):
    """微博专用二跳搜索，优先定位话题页或代表微博页。"""

    name = "weibo_secondary_search"

    def _domains_for_channel(self, channel_code: str) -> tuple[str, ...]:
        return ("weibo.com", "s.weibo.com")

    def _build_search_url(self, title: str, domain: str) -> str:
        query = quote_plus(f"site:weibo.com OR site:s.weibo.com {title}".strip())
        return f"https://www.bing.com/search?q={query}&setlang=zh-CN"

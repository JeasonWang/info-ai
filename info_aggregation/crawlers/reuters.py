"""
信息聚合系统 - 路透社爬虫
爬取路透社国际新闻，并深入爬取详情页获取完整内容
"""
import hashlib
import html as html_lib
import json
import re
from datetime import datetime
from xml.etree import ElementTree

import requests

from .base import BaseCrawler
from services.collection.detail_pipeline import DetailStrategyResult, limit_detail_content, run_detail_pipeline
from services.collection.html_article_extractor import HtmlArticleExtractor


class ReutersCrawler(BaseCrawler):
    """
    路透社爬虫
    通过路透社RSS和网页端获取国际新闻
    爬取频率：每2小时一次
    """

    NEWS_API = "https://www.reuters.com/pf/api/v3/content/fetch/articles-by-section-alias-or-id-v1"
    RSS_URL = "https://www.reutersagency.com/feed/"
    WORLD_URL = "https://www.reuters.com/world/"
    ARTICLE_API = "https://www.reuters.com/pf/api/v3/content/fetch/article-by-id-or-url-v1"
    NEWS_SITEMAP = "https://www.reuters.com/arc/outboundfeeds/news-sitemap/?outputType=xml"
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q=site:reuters.com%20Reuters%20world&hl=en-US&gl=US&ceid=US:en"
    SITEMAP_CATEGORY_PREFIXES = (
        "https://www.reuters.com/world/",
        "https://www.reuters.com/business/",
        "https://www.reuters.com/markets/",
        "https://www.reuters.com/technology/",
        "https://www.reuters.com/legal/",
    )

    def __init__(self):
        super().__init__("reuters", "路透社")

    def crawl(self) -> list:
        results = []
        try:
            results = self._crawl_api()
            if results:
                return results
        except Exception:
            pass

        try:
            results = self._crawl_rss()
            if results:
                return results
        except Exception:
            pass

        try:
            results = self._crawl_web_page()
            if results:
                return results
        except Exception as e:
            self.logger.error(f"路透社爬取异常: {e}")

        try:
            results = self._crawl_news_sitemap()
            if results:
                return results
        except Exception as e:
            self.logger.warning(f"路透社新闻 sitemap 兜底失败: {e}")

        try:
            results = self._crawl_google_news_index()
            if results:
                return results
        except Exception as e:
            self.logger.warning(f"路透社新闻索引兜底失败: {e}")
        return results

    def _crawl_news_sitemap(self) -> list:
        """Reuters 官方网页入口 401 时，使用公开新闻 sitemap 恢复官方 URL 与发布时间。"""
        headers = self._build_headers()
        headers["Accept"] = "application/xml,text/xml,*/*"
        headers["Referer"] = "https://www.reuters.com/"
        response = self.fetch(self.NEWS_SITEMAP, headers=headers, timeout=12)
        root = ElementTree.fromstring(response.text.strip())
        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }
        results = []
        seen = set()
        for url_node in root.findall("sm:url", ns):
            source_url = url_node.findtext("sm:loc", default="", namespaces=ns).strip()
            if not source_url.startswith(self.SITEMAP_CATEGORY_PREFIXES):
                continue
            title = url_node.findtext("news:news/news:title", default="", namespaces=ns).strip()
            published_at = url_node.findtext("news:news/news:publication_date", default="", namespaces=ns).strip()
            keywords = url_node.findtext("news:news/news:keywords", default="", namespaces=ns).strip()
            tickers = url_node.findtext("news:news/news:stock_tickers", default="", namespaces=ns).strip()
            captions = [
                caption.text.strip()
                for caption in url_node.findall("image:image/image:caption", ns)
                if caption.text and caption.text.strip()
            ]
            if not title or source_url in seen:
                continue
            seen.add(source_url)
            source_id = hashlib.md5(f"reuters_sitemap_{source_url}".encode()).hexdigest()[:16]
            metadata = self._merge_distinct_parts([
                title,
                f"Reuters category: {self._category_from_url(source_url)}." if self._category_from_url(source_url) else "",
                f"Reuters Published at {published_at} according to its official news sitemap." if published_at else "Reuters published this item according to its official news sitemap.",
                f"Reuters image context: {' '.join(captions[:2])}" if captions else "",
                f"Reuters stock tickers: {tickers}." if tickers else "",
                f"Reuters news codes: {', '.join(self._extract_news_codes(keywords)[:5])}." if keywords else "",
                f"Official Reuters URL: {source_url}",
            ])
            results.append({
                "source_id": source_id,
                "title": title[:200],
                "content": metadata[:800],
                "source_url": source_url,
                "event_time": self._parse_reuters_datetime(published_at) or datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "published_at" if published_at else "",
                "indicator_value": published_at[:100],
                "_allow_title_only": True,
                "_reuters_source": "news_sitemap",
            })
            if len(results) >= 20:
                break
        return results

    def _parse_reuters_datetime(self, value: str) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _category_from_url(self, source_url: str) -> str:
        match = re.search(r"reuters\.com/([^/]+(?:/[^/]+)?)/", source_url or "")
        return match.group(1).replace("/", " / ") if match else ""

    def _extract_news_codes(self, keywords: str) -> list[str]:
        codes: list[str] = []
        seen: set[str] = set()
        for code in re.findall(r"(?:USN|newsml)_([A-Z0-9]+)", keywords or ""):
            if code in seen:
                continue
            seen.add(code)
            codes.append(code)
        return codes

    def _crawl_api(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.reuters.com/world/"
        params = {
            "size": 20,
            "section_alias": "world",
        }
        data = self.fetch_json(self.NEWS_API, params=params, headers=headers)
        articles = data.get("result", {}).get("articles", [])
        results = []
        for article in articles[:20]:
            title = article.get("title", "").strip()
            if not title:
                continue
            article_id = article.get("id", "")
            source_id = hashlib.md5(f"reuters_{article_id}".encode()).hexdigest()[:16]
            summary = article.get("description", title)[:500]
            article_url = article.get("canonical_url", article.get("url", ""))
            if article_url and not article_url.startswith("http"):
                article_url = f"https://www.reuters.com{article_url}"
            if not article_url:
                article_url = f"https://www.reuters.com/world/{article_id}/"
            results.append({
                "source_id": source_id,
                "title": title[:200],
                "content": summary,
                "source_url": article_url,
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
        return results

    def _crawl_rss(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.reutersagency.com/"
        response = self.fetch(self.RSS_URL, headers=headers)
        xml_text = response.text
        results = []
        item_pattern = re.findall(r'<item>\s*<title><!\[CDATA\[(.*?)\]\]></title>.*?<link>(.*?)</link>.*?<description><!\[CDATA\[(.*?)\]\]></description>', xml_text, re.DOTALL)
        if not item_pattern:
            item_pattern = re.findall(r'<item>\s*<title>(.*?)</title>.*?<link>(.*?)</link>.*?<description>(.*?)</description>', xml_text, re.DOTALL)
        for title, link, desc in item_pattern[:20]:
            title = title.strip()
            if not title:
                continue
            source_id = hashlib.md5(f"reuters_{link}".encode()).hexdigest()[:16]
            desc = desc.strip() if desc else title
            results.append({
                "source_id": source_id,
                "title": title[:200],
                "content": desc[:500],
                "source_url": link.strip(),
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
        return results

    def _crawl_web_page(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.reuters.com/"
        response = self.fetch(self.WORLD_URL, headers=headers)
        html = response.text
        results = []
        link_pattern = re.findall(r'href="(/world/[^"]+)"[^>]*>[\s\S]*?<span[^>]*>([^<]+)</span>', html, re.DOTALL)
        if not link_pattern:
            link_pattern = re.findall(r'href="(/world/[^"]+-\d{4}-\d{2}-\d{2}[^"]*)"[^>]*>([^<]{10,}?)</a>', html, re.DOTALL)
        seen = set()
        for path, title in link_pattern[:20]:
            title = title.strip()
            if not title or path in seen:
                continue
            seen.add(path)
            url = f"https://www.reuters.com{path}"
            source_id = hashlib.md5(f"reuters_{path}".encode()).hexdigest()[:16]
            results.append({
                "source_id": source_id,
                "title": title[:200],
                "content": title[:500],
                "source_url": url,
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
        return results

    def _crawl_google_news_index(self) -> list:
        """Reuters 官方入口不可访问时，使用新闻索引恢复真实 Reuters 线索，不伪造正文。"""

        headers = self._build_headers()
        headers["Referer"] = "https://news.google.com/"
        response = self.fetch(self.GOOGLE_NEWS_RSS, headers=headers, timeout=12)
        root = ElementTree.fromstring(response.text)
        results = []
        seen = set()
        for item in root.findall(".//item")[:30]:
            raw_title = self._xml_text(item, "title")
            link = self._xml_text(item, "link")
            raw_description = html_lib.unescape(self._xml_text(item, "description"))
            description = self._clean_detail_text(raw_description)
            source = self._xml_text(item, "source")
            if source and "Reuters" not in source:
                continue
            title = re.sub(r"\s+-\s+Reuters\s*$", "", raw_title).strip()
            if not title or not link or title in seen:
                continue
            seen.add(title)
            official_url = self._extract_reuters_url_from_index_description(raw_description)
            source_url = official_url or link
            source_id = hashlib.md5(f"reuters_google_news_{source_url or title}".encode()).hexdigest()[:16]
            summary = description or f"Reuters indexed news item: {title}"
            results.append({
                "source_id": source_id,
                "title": title[:200],
                "content": summary[:500],
                "source_url": source_url,
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
                "_allow_title_only": True,
                "_reuters_source": "google_news_index",
                "_reuters_index_url": link,
                "_reuters_lineage": "official_url_from_index" if official_url else "index_summary_only",
            })
            if len(results) >= 20:
                break
        return results

    def _extract_reuters_url_from_index_description(self, description: str) -> str:
        """从新闻索引摘要中恢复 Reuters 官方 URL，能恢复时后续继续尝试全文抓取。"""
        match = re.search(r'https://www\.reuters\.com/[^"\s<>]+', description or "")
        if not match:
            return ""
        return html_lib.unescape(match.group(0)).rstrip(".,)")

    def _xml_text(self, item, tag: str) -> str:
        node = item.find(tag)
        return (node.text or "").strip() if node is not None else ""

    def fetch_detail(self, source_url: str, item: dict) -> str:
        return self.resolve_detail(item).content

    def resolve_detail(self, item: dict):
        candidates = []
        is_google_index = item.get("_reuters_source") == "google_news_index" or "news.google.com" in item.get("source_url", "")
        has_official_url = str(item.get("source_url", "")).startswith("https://www.reuters.com/")
        is_sitemap_metadata = item.get("_reuters_source") == "news_sitemap" or self._looks_like_sitemap_metadata(item)
        if is_google_index and not has_official_url:
            summary = self._clean_detail_text(item.get("content", ""))
            if len(summary) >= 50:
                candidates.append(DetailStrategyResult(strategy="news_index_summary", content=limit_detail_content(summary)))
                return run_detail_pipeline(
                    title=item.get("title", ""),
                    list_content=item.get("content", ""),
                    strategy_results=candidates,
                    channel_code=self.channel_code,
                )
        if is_sitemap_metadata:
            metadata = self._clean_detail_text(item.get("content", ""))
            if len(metadata) >= 50:
                candidates.append(DetailStrategyResult(strategy="news_sitemap_metadata", content=limit_detail_content(metadata)))
                return run_detail_pipeline(
                    title=item.get("title", ""),
                    list_content=item.get("content", ""),
                    strategy_results=candidates,
                    channel_code=self.channel_code,
                )

        api_detail = self._fetch_article_api_detail(item)
        if api_detail:
            candidates.append(api_detail)

        json_ld_detail = self._fetch_json_ld_detail(item)
        if json_ld_detail:
            candidates.append(json_ld_detail)

        html_detail = self._fetch_html_article_detail(item)
        if html_detail:
            candidates.append(html_detail)

        if is_google_index:
            summary = self._clean_detail_text(item.get("content", ""))
            if len(summary) >= 50:
                candidates.append(DetailStrategyResult(strategy="news_index_summary", content=limit_detail_content(summary)))
        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )

    def _looks_like_sitemap_metadata(self, item: dict) -> bool:
        content = item.get("content", "") or ""
        source_url = item.get("source_url", "") or ""
        return (
            source_url.startswith("https://www.reuters.com/")
            and "official news sitemap" in content
            and "Official Reuters URL:" in content
        )

    def _fetch_article_api_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.reuters.com/"
            post_headers = headers.copy()
            post_headers["Content-Type"] = "application/json"
            response = self.session.post(
                self.ARTICLE_API,
                data=json.dumps({"url": source_url}),
                headers=post_headers,
                timeout=15,
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            article = response.json().get("result", {})
            texts = []
            for part in article.get("content_items", []) or []:
                if part.get("type") != "paragraph":
                    continue
                text = self._clean_detail_text(part.get("content", ""))
                if text:
                    texts.append(text)
            rn_text = self._clean_detail_text(article.get("rn_text", ""))
            if rn_text:
                texts.append(rn_text)
            combined = self._merge_distinct_parts(texts)
            if len(combined) >= 50:
                return DetailStrategyResult(strategy="reuters_article_api", content=limit_detail_content(combined))
        except requests.HTTPError as e:
            result = self._http_failure_result("reuters_article_api", e)
            self.logger.warning(f"路透社详情 API 被阻断: {result.failure_reason}")
            return result
        except Exception as e:
            self.logger.warning(f"路透社详情爬取失败: {e}")
        return None

    def _fetch_json_ld_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.reuters.com/"
            html = self.fetch(source_url, headers=headers).text
            for raw_json in re.findall(
                r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                html,
                re.DOTALL | re.IGNORECASE,
            ):
                try:
                    data = json.loads(raw_json.strip())
                except json.JSONDecodeError:
                    continue
                nodes = data if isinstance(data, list) else [data]
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    body = self._clean_detail_text(node.get("articleBody", ""))
                    if len(body) >= 50:
                        return DetailStrategyResult(strategy="reuters_json_ld", content=limit_detail_content(body))
        except requests.HTTPError as e:
            result = self._http_failure_result("reuters_json_ld", e)
            self.logger.warning(f"路透社JSON-LD详情请求被阻断: {result.failure_reason}")
            return result
        except Exception as e:
            self.logger.warning(f"路透社JSON-LD详情解析失败: {e}")
        return None

    def _fetch_html_article_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.reuters.com/"
            html = self.fetch(source_url, headers=headers).text
            text = HtmlArticleExtractor().extract(html)
            if len(text) >= 50:
                return DetailStrategyResult(strategy="html_article", content=limit_detail_content(text))
        except requests.HTTPError as e:
            result = self._http_failure_result("html_article", e)
            self.logger.warning(f"路透社HTML正文请求被阻断: {result.failure_reason}")
            return result
        except Exception as e:
            self.logger.warning(f"路透社HTML正文兜底失败: {e}")
        return None

    def _http_failure_result(self, strategy: str, error: requests.HTTPError) -> DetailStrategyResult:
        status_code = error.response.status_code if error.response is not None else 0
        if status_code in (401, 403):
            reason = f"http_{status_code}_blocked"
        elif status_code == 404:
            reason = "http_404_not_found"
        else:
            reason = f"http_{status_code}_error" if status_code else "http_error"
        return DetailStrategyResult(strategy=strategy, content="", failure_reason=reason, matched_rules=[f"http_{status_code}"] if status_code else ["http_error"])

    def _clean_detail_text(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value or "")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _merge_distinct_parts(self, parts: list[str]) -> str:
        merged = []
        seen = set()
        for part in parts:
            text = self._clean_detail_text(part)
            if not text or text in seen:
                continue
            if any(text in existing or existing in text for existing in merged):
                continue
            merged.append(text)
            seen.add(text)
        return " ".join(merged)

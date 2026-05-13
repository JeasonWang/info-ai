"""
信息聚合系统 - CSDN爬虫
爬取CSDN热门技术文章，并深入爬取详情页获取完整内容
"""
import hashlib
import html as html_lib
import re
from datetime import datetime

from .base import BaseCrawler
from services.collection.detail_pipeline import DetailStrategyResult, limit_detail_content, run_detail_pipeline


class CSDNCrawler(BaseCrawler):
    """
    CSDN爬虫
    通过CSDN网页端获取热门技术文章
    爬取频率：每2小时一次
    """

    HOT_API = "https://blog.csdn.net/api-user/feed/hot_article"
    HOME_URL = "https://www.csdn.net/nav/ai"

    def __init__(self):
        super().__init__("csdn", "CSDN")

    def _clean_content_text(self, value: str) -> str:
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', str(value or ''), flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _extract_web_fallback_content(self, html: str, title: str) -> str:
        """优先从正文块提取 CSDN 文章内容，减少社区壳页面噪声干扰。"""
        block_patterns = [
            r'<article[^>]*id="article_content"[^>]*>(.*?)</article>',
            r'<article[^>]*class="[^"]*article_content[^"]*"[^>]*>(.*?)</article>',
            r"<article[^>]*>(.*?)</article>",
            r"<main[^>]*>(.*?)</main>",
        ]
        cleaned_blocks = []
        for pattern in block_patterns:
            for match in re.findall(pattern, html, re.DOTALL | re.IGNORECASE):
                cleaned = self._clean_content_text(match)
                if cleaned:
                    cleaned_blocks.append(cleaned)

        for block in cleaned_blocks:
            if title and title in block and len(block) >= 40:
                return block

        for block in cleaned_blocks:
            if len(block) >= 80:
                return block

        fallback_text = self._extract_text_from_html(html)
        if title and title in fallback_text:
            return fallback_text
        return fallback_text

    def crawl(self) -> list:
        results = []
        try:
            results = self._crawl_api()
            if results:
                return results
        except Exception:
            pass

        try:
            results = self._crawl_web_page()
            if results:
                return results
        except Exception as e:
            self.logger.error(f"CSDN爬取异常: {e}")
        return results

    def _crawl_api(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://blog.csdn.net/"
        data = self.fetch_json(self.HOT_API, headers=headers)
        articles = data.get("data", [])
        results = []
        for article in articles[:20]:
            title = article.get("title", "").strip()
            if not title:
                continue
            article_id = article.get("article_id", "")
            source_id = hashlib.md5(f"csdn_{article_id}".encode()).hexdigest()[:16]
            desc = article.get("desc", title)[:500]
            url = article.get("url", f"https://blog.csdn.net/article/details/{article_id}")
            results.append({
                "source_id": source_id,
                "title": title[:200],
                "content": desc,
                "source_url": url,
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
                "_allow_title_only": True,
            })
        return results

    def _crawl_web_page(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.csdn.net/"
        response = self.fetch(self.HOME_URL, headers=headers)
        html = response.text
        results = []
        article_pattern = re.findall(
            r'<a[^>]*href="(https://blog\.csdn\.net/[^/]+/article/details/(\d+))"[^>]*>\s*<span[^>]*>([^<]+)</span>',
            html, re.DOTALL
        )
        if not article_pattern:
            article_pattern = re.findall(
                r'<a[^>]*href="(https://blog\.csdn\.net/[^"]+article/details/(\d+))"[^>]*title="([^"]*)"',
                html, re.DOTALL
            )
        if not article_pattern:
            article_pattern = []
            generic_links = re.findall(
                r'<a[^>]*href="(https://blog\.csdn\.net/[^"\']+article/details/(\d+))"[^>]*>(.*?)</a>',
                html,
                re.DOTALL | re.IGNORECASE,
            )
            for url, article_id, raw_title in generic_links:
                title = self._clean_content_text(html_lib.unescape(raw_title))
                article_pattern.append((url, article_id, title))
        seen = set()
        for url, article_id, title in article_pattern:
            title = title.strip()
            if not title or article_id in seen or self._is_non_article_title(title):
                continue
            seen.add(article_id)
            source_id = hashlib.md5(f"csdn_{article_id}".encode()).hexdigest()[:16]
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
            if len(results) >= 20:
                break
        return results

    def _is_non_article_title(self, title: str) -> bool:
        noise_titles = {"账号管理规范", "版权申诉", "版权与免责声明", "Chrome商店下载"}
        return title in noise_titles or len(title) < 6

    def fetch_detail(self, source_url: str, item: dict) -> str:
        return self.resolve_detail(item).content

    def resolve_detail(self, item: dict):
        candidates = []

        article_detail = self._fetch_article_detail_content(item)
        if article_detail:
            candidates.append(article_detail)

        web_fallback = self._fetch_web_fallback(item)
        if web_fallback:
            candidates.append(web_fallback)

        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )

    def _fetch_article_detail_content(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://blog.csdn.net/"
            response = self.fetch(source_url, headers=headers)
            html = response.text
            content = ""
            match = re.search(r'<article[^>]*id="article_content"[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
            if not match:
                match = re.search(r'<article[^>]*class="[^"]*article_content[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
            if match:
                content = self._clean_content_text(match.group(1))

            if content and len(content) >= 50:
                return DetailStrategyResult(strategy="fetch_detail", content=limit_detail_content(content))
        except Exception as e:
            self.logger.warning(f"CSDN详情页正文解析失败: {e}")

        return None

    def _fetch_web_fallback(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://blog.csdn.net/"
            response = self.fetch(source_url, headers=headers)
            html = response.text
            text = self._extract_web_fallback_content(html, item.get("title", ""))
            if text and len(text) >= 50:
                return DetailStrategyResult(strategy="web_fallback", content=limit_detail_content(text))
        except Exception as e:
            self.logger.warning(f"CSDN网页兜底解析失败: {e}")

        return None

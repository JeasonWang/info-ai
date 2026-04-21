"""
信息聚合系统 - 掘金爬虫
爬取掘金热门技术文章，并深入爬取详情页获取完整内容
"""
import hashlib
import json
import re
from datetime import datetime

from .base import BaseCrawler
from services.detail_pipeline import DetailStrategyResult, run_detail_pipeline


class JuejinCrawler(BaseCrawler):
    """
    掘金爬虫
    通过掘金API和网页端获取热门技术文章
    爬取频率：每2小时一次
    """

    RECOMMEND_API = "https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed"
    DETAIL_API = "https://api.juejin.cn/content_api/v1/article/detail"
    HOME_URL = "https://juejin.cn/"

    def __init__(self):
        super().__init__("juejin", "掘金")

    def _clean_markdown_text(self, value: str) -> str:
        cleaned = re.sub(r'```[\s\S]*?```', '', str(value or ''))
        cleaned = re.sub(r'[#*`>\-\[\]()!|]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _clean_html_text(self, value: str) -> str:
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', str(value or ''), flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _merge_distinct_parts(self, parts: list[str], prefix: str = "") -> str:
        """按顺序合并掘金详情片段，并去掉重复前缀和包含式重复。"""
        merged_parts = []
        seen = set()

        if prefix:
            normalized_prefix = re.sub(r"\s+", " ", str(prefix or "")).strip()
            if normalized_prefix:
                merged_parts.append(normalized_prefix)
                seen.add(normalized_prefix)

        for part in parts:
            normalized = re.sub(r"\s+", " ", str(part or "")).strip()
            if not normalized or normalized in seen:
                continue
            for existing in merged_parts:
                if normalized.startswith(existing):
                    normalized = normalized[len(existing):].lstrip("，。,:：;； ")
            if not normalized:
                continue
            if any(normalized in existing or existing in normalized for existing in merged_parts):
                continue
            merged_parts.append(normalized)
            seen.add(normalized)

        return " ".join(merged_parts).strip()

    def _extract_web_fallback_content(self, html: str, title: str) -> str:
        """优先从文章正文块提取内容，减少掘金壳页面噪声污染。"""
        block_patterns = [
            r"<article[^>]*>(.*?)</article>",
            r'<div[^>]*class="[^"]*(?:article|content|detail|body)[^"]*"[^>]*>(.*?)</div>',
            r"<main[^>]*>(.*?)</main>",
        ]

        cleaned_blocks = []
        for pattern in block_patterns:
            for match in re.findall(pattern, html, re.DOTALL | re.IGNORECASE):
                cleaned = self._clean_html_text(match)
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
            self.logger.error(f"掘金爬取异常: {e}")
        return results

    def _crawl_api(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://juejin.cn/"
        headers["Content-Type"] = "application/json"
        payload = json.dumps({"id_type": 2, "sort_type": 200, "cursor": "0", "limit": 20})
        response = self.session.post(
            self.RECOMMEND_API,
            data=payload,
            headers=headers,
            timeout=15,
        )
        data = response.json()
        articles = data.get("data", [])
        results = []
        for article in articles[:20]:
            article_info = article.get("article_info", {})
            title = article_info.get("title", "").strip()
            if not title:
                continue
            article_id = article_info.get("article_id", "")
            source_id = hashlib.md5(f"juejin_{article_id}".encode()).hexdigest()[:16]
            brief = article_info.get("brief_content", title)[:500]
            results.append({
                "source_id": source_id,
                "title": title[:40],
                "content": brief,
                "source_url": f"https://juejin.cn/post/{article_id}",
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
        return results

    def _crawl_web_page(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://juejin.cn/"
        response = self.fetch(self.HOME_URL, headers=headers)
        html = response.text
        results = []
        post_pattern = re.findall(r'href="/post/(\d+)"[^>]*>([^<]{4,}?)</a>', html, re.DOTALL)
        if not post_pattern:
            post_pattern = re.findall(r'/post/(\d+)[^>]*title="([^"]+)"', html, re.DOTALL)
        seen = set()
        for article_id, title in post_pattern[:20]:
            title = title.strip()
            if not title or article_id in seen:
                continue
            seen.add(article_id)
            source_id = hashlib.md5(f"juejin_{article_id}".encode()).hexdigest()[:16]
            results.append({
                "source_id": source_id,
                "title": title[:40],
                "content": title[:500],
                "source_url": f"https://juejin.cn/post/{article_id}",
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
        return results

    def fetch_detail(self, source_url: str, item: dict) -> str:
        return self.resolve_detail(item).content

    def resolve_detail(self, item: dict):
        candidates = []

        api_detail = self._fetch_api_detail(item)
        if api_detail:
            candidates.append(api_detail)

        web_fallback = self._fetch_web_fallback(item)
        if web_fallback:
            candidates.append(web_fallback)

        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
        )

    def _fetch_api_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://juejin.cn/"
            headers["Content-Type"] = "application/json"
            article_id = source_url.split("/post/")[-1].rstrip("/")
            payload = json.dumps({"article_id": article_id})
            response = self.session.post(
                self.DETAIL_API,
                data=payload,
                headers=headers,
                timeout=15,
            )
            data = response.json()
            article_data = data.get("data", {}).get("article_info", {})
            parts = []

            mark_content = self._clean_markdown_text(article_data.get("mark_content", ""))
            if len(mark_content) >= 12:
                parts.append(mark_content)

            content = self._clean_html_text(article_data.get("content", ""))
            if len(content) >= 12:
                parts.append(content)

            combined = self._merge_distinct_parts(parts)
            if len(combined) >= 20:
                return DetailStrategyResult(strategy="fetch_detail", content=combined[:500])
        except Exception as e:
            self.logger.warning(f"掘金API详情解析失败: {e}")

        return None

    def _fetch_web_fallback(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://juejin.cn/"
            headers["Content-Type"] = "application/json"
            response = self.fetch(source_url, headers=headers)
            html = response.text
            text = self._extract_web_fallback_content(html, item.get("title", ""))
            if text and len(text) >= 20:
                return DetailStrategyResult(strategy="web_fallback", content=text[:500])
        except Exception as e:
            self.logger.warning(f"掘金网页兜底解析失败: {e}")

        return None

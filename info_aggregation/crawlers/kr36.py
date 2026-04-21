"""
信息聚合系统 - 36氪爬虫
爬取36氪AI/大模型相关热门文章，并深入爬取详情页获取完整内容
"""
import hashlib
import json
import re
from datetime import datetime

from .base import BaseCrawler
from services.detail_pipeline import DetailStrategyResult, run_detail_pipeline


class Kr36Crawler(BaseCrawler):
    """
    36氪爬虫
    通过36氪API和网页端获取热门科技文章
    爬取频率：每2小时一次
    """

    HOT_API = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
    DETAIL_API = "https://gateway.36kr.com/api/mis/article/detail"
    HOT_URL = "https://36kr.com/hot-list/catalog"
    AI_URL = "https://36kr.com/information/AI"

    def __init__(self):
        super().__init__("36kr", "36氪")

    def _clean_content_text(self, value: str) -> str:
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', str(value or ''), flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _merge_distinct_parts(self, parts: list[str], prefix: str = "") -> str:
        """按顺序合并 36 氪正文片段，并尽量去掉包含式重复。"""
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
        """优先抽取正文块，减少壳页面和推荐区噪声进入兜底正文。"""
        block_patterns = [
            r"<article[^>]*>(.*?)</article>",
            r'<div[^>]*class="[^"]*(?:article-content|content|article|detail|body)[^"]*"[^>]*>(.*?)</div>',
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
            self.logger.error(f"36氪爬取异常: {e}")
        return results

    def _crawl_api(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://36kr.com/"
        headers["Content-Type"] = "application/json"
        payload = json.dumps({"partner_id": "wap", "pageSize": 20})
        response = self.session.post(
            self.HOT_API,
            data=payload,
            headers=headers,
            timeout=15,
        )
        data = response.json()
        items = data.get("data", {}).get("hotRankList", [])
        if not items:
            items = data.get("data", {}).get("items", [])
        results = []
        for item in items[:20]:
            title = item.get("title", "").strip()
            if not title:
                continue
            article_id = item.get("entityId", item.get("id", ""))
            source_id = hashlib.md5(f"36kr_{article_id}".encode()).hexdigest()[:16]
            summary = item.get("summary", item.get("description", title))[:500]
            results.append({
                "source_id": source_id,
                "title": title[:40],
                "content": summary,
                "source_url": f"https://36kr.com/p/{article_id}",
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
        return results

    def _crawl_web_page(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://36kr.com/"
        for url in [self.HOT_URL, self.AI_URL]:
            try:
                response = self.fetch(url, headers=headers)
                html = response.text
                results = self._parse_article_list(html)
                if results:
                    return results
            except Exception:
                continue
        return []

    def _parse_article_list(self, html: str) -> list:
        results = []
        try:
            match = re.search(r'window\.initialState\s*=\s*({.*?});\s*</script>', html, re.DOTALL)
            if match:
                json_str = match.group(1)
                state = json.loads(json_str)
                articles = state.get("hotListModule", {}).get("hotList", [])
                if not articles:
                    articles = state.get("catalogListModule", {}).get("catalogList", [])
                if not articles:
                    articles = state.get("articleListModule", {}).get("articleList", [])
                for article in articles[:20]:
                    title = article.get("title", "").strip()
                    if not title:
                        continue
                    article_id = article.get("entityId", article.get("id", ""))
                    source_id = hashlib.md5(f"36kr_{article_id}".encode()).hexdigest()[:16]
                    summary = article.get("summary", title)[:500]
                    results.append({
                        "source_id": source_id,
                        "title": title[:40],
                        "content": summary,
                        "source_url": f"https://36kr.com/p/{article_id}",
                        "event_time": datetime.now(),
                        "core_entity": title[:20],
                        "location": "",
                        "indicator_name": "",
                        "indicator_value": "",
                    })
        except Exception as e:
            self.logger.warning(f"36氪页面解析失败: {e}")

        if not results:
            article_pattern = re.findall(r'href="/p/(\d+)"[^>]*>([^<]{6,}?)</a>', html, re.DOTALL)
            seen = set()
            for article_id, title in article_pattern[:20]:
                title = title.strip()
                if not title or article_id in seen:
                    continue
                seen.add(article_id)
                source_id = hashlib.md5(f"36kr_{article_id}".encode()).hexdigest()[:16]
                results.append({
                    "source_id": source_id,
                    "title": title[:40],
                    "content": title[:500],
                    "source_url": f"https://36kr.com/p/{article_id}",
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
            headers["Referer"] = "https://36kr.com/"
            headers["Content-Type"] = "application/json"
            article_id = source_url.split("/p/")[-1].rstrip("/")
            payload = json.dumps({"articleId": article_id})
            response = self.session.post(
                self.DETAIL_API,
                data=payload,
                headers=headers,
                timeout=15,
            )
            data = response.json()
            article_data = data.get("data", {}).get("articleDetail", {})
            if not article_data:
                article_data = data.get("data", {})

            content = self._extract_api_content(article_data)
            if content:
                return DetailStrategyResult(strategy="fetch_detail", content=content)
        except Exception as e:
            self.logger.warning(f"36氪API详情解析失败: {e}")

        return None

    def _extract_api_content(self, article_data: dict) -> str:
        """兼容36氪不同返回结构，尽量从API里拿到完整正文。"""
        candidates = []

        for key in ("content", "articleContent", "body", "markdownContent"):
            value = article_data.get(key, "")
            if isinstance(value, str):
                candidates.append(value)
            elif isinstance(value, dict):
                candidates.extend(str(value.get(field, "")) for field in ("content", "body", "text", "html"))

        summary = article_data.get("summary", "")
        if isinstance(summary, str):
            candidates.append(summary)

        nested_nodes = [
            article_data.get("articleDetail", {}),
            article_data.get("article", {}),
            article_data.get("data", {}),
        ]
        for nested in nested_nodes:
            if isinstance(nested, dict):
                for key in ("content", "articleContent", "body", "summary", "markdownContent"):
                    value = nested.get(key, "")
                    if isinstance(value, str):
                        candidates.append(value)
                    elif isinstance(value, dict):
                        candidates.extend(str(value.get(field, "")) for field in ("content", "body", "text", "html"))

        cleaned_parts = []
        for raw_content in candidates:
            content = self._clean_content_text(raw_content)
            if len(content) >= 12:
                cleaned_parts.append(content)

        combined = self._merge_distinct_parts(cleaned_parts)
        if len(combined) >= 20:
            return combined[:500]

        return ""

    def _fetch_web_fallback(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://36kr.com/"
            headers["Content-Type"] = "application/json"
            response = self.fetch(source_url, headers=headers)
            html = response.text

            text = self._extract_web_fallback_content(html, item.get("title", ""))
            if text and len(text) >= 20:
                return DetailStrategyResult(strategy="web_fallback", content=text[:500])
        except Exception as e:
            self.logger.warning(f"36氪网页兜底解析失败: {e}")

        return None

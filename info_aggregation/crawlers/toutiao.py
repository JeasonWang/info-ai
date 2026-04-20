"""
信息聚合系统 - 今日头条爬虫
爬取今日头条热点新闻，并深入爬取详情页获取完整内容
"""
import hashlib
import re
from datetime import datetime
from urllib.parse import quote

from .base import BaseCrawler
from services.detail_pipeline import DetailStrategyResult, run_detail_pipeline


class ToutiaoCrawler(BaseCrawler):
    """
    今日头条爬虫
    通过头条热点API获取热点新闻
    爬取频率：每30分钟一次
    """

    TREND_API = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    DETAIL_API = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    ARTICLE_API = "https://www.toutiao.com/article/{article_id}/"

    def __init__(self):
        super().__init__("toutiao", "今日头条")

    def _merge_distinct_parts(self, parts: list[str], prefix: str = "") -> str:
        """按顺序合并正文片段，并去掉重复内容。"""
        merged_parts = []
        seen = set()

        if prefix:
            normalized_prefix = prefix.strip()
            if normalized_prefix:
                merged_parts.append(normalized_prefix)
                seen.add(normalized_prefix)

        for part in parts:
            normalized = re.sub(r"\s+", " ", str(part or "")).strip()
            if not normalized or normalized in seen:
                continue
            merged_parts.append(normalized)
            seen.add(normalized)

        return " ".join(merged_parts).strip()

    def crawl(self) -> list:
        results = []
        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.toutiao.com/"
            data = self.fetch_json(self.TREND_API, headers=headers)
            items = data.get("data", [])
            for item in items[:20]:
                title = item.get("Title", "").strip()
                if not title:
                    continue
                cluster_id = item.get("ClusterId", "")
                source_id = hashlib.md5(f"toutiao_{cluster_id}".encode()).hexdigest()[:16]
                hot_desc = item.get("HotDesc", "")
                label = item.get("Label", "")
                content_parts = [title]
                if hot_desc and hot_desc != title:
                    content_parts.append(hot_desc)
                if label and label != title:
                    content_parts.append(label)
                content = "。".join(content_parts)
                results.append({
                    "source_id": source_id,
                    "title": title[:40],
                    "content": content[:500],
                    "source_url": f"https://www.toutiao.com/trending/{cluster_id}/",
                    "event_time": datetime.now(),
                    "core_entity": title[:20],
                    "location": "",
                    "indicator_name": "",
                    "indicator_value": "",
                    "_cluster_id": cluster_id,
                    "_hot_desc": hot_desc,
                    "_label": label,
                })
        except Exception as e:
            self.logger.error(f"头条爬取异常: {e}")
        return results

    def fetch_detail(self, source_url: str, item: dict) -> str:
        result = self.resolve_detail(item)
        return result.content

    def resolve_detail(self, item: dict):
        candidates = []

        hot_board_detail = self._fetch_hot_board_detail(item)
        if hot_board_detail:
            candidates.append(hot_board_detail)

        search_content = self._fetch_search_content(item)
        if search_content:
            candidates.append(search_content)

        web_fallback = self._fetch_web_fallback(item)
        if web_fallback:
            candidates.append(web_fallback)

        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
        )

    def _build_detail_headers(self) -> dict:
        headers = self._build_headers()
        headers["Referer"] = "https://www.toutiao.com/"
        headers["Accept"] = "application/json, text/plain, */*"
        return headers

    def _extract_cluster_id(self, item: dict) -> str:
        cluster_id = str(item.get("_cluster_id", "")).strip()
        if cluster_id:
            return cluster_id
        source_url = item.get("source_url", "")
        cluster_id_match = re.search(r"/trending/(\d+)", source_url)
        if cluster_id_match:
            return cluster_id_match.group(1)
        return ""

    def _fetch_hot_board_detail(self, item: dict):
        cluster_id = self._extract_cluster_id(item)
        if not cluster_id:
            return None

        try:
            detail_api = f"{self.DETAIL_API}&cluster_id={cluster_id}"
            detail_data = self.fetch_json(detail_api, headers=self._build_detail_headers())
            articles = detail_data.get("data", [])
            target_item = None
            for article in articles:
                if str(article.get("ClusterId", "")) == str(cluster_id):
                    target_item = article
                    break
            if not target_item and articles:
                target_item = articles[0]

            if not target_item:
                return None

            content_parts = []
            for key in ("Title", "HotDesc", "Abstract"):
                value = str(target_item.get(key, "")).strip()
                if value:
                    content_parts.append(value)
            label = str(target_item.get("Label", "")).strip()
            if label:
                content_parts.append(f"标签：{label}")

            combined = self._merge_distinct_parts(content_parts)
            if combined:
                return DetailStrategyResult(strategy="hot_board_detail", content=combined[:500])
        except Exception:
            return None
        return None

    def _fetch_search_content(self, item: dict):
        word = str(item.get("title", "")).strip()
        if not word:
            return None

        try:
            search_url = f"https://www.toutiao.com/api/search/content/?keyword={quote(word)}&count=5"
            search_data = self.fetch_json(search_url, headers=self._build_detail_headers())
            search_items = search_data.get("data", [])
            merged_parts = []
            for search_item in search_items[:3]:
                for key in ("title", "abstract", "content"):
                    value = re.sub(r"<[^>]+>", "", str(search_item.get(key, "")))
                    value = re.sub(r"\s+", " ", value).strip()
                    if value:
                        merged_parts.append(value)
            combined = self._merge_distinct_parts(merged_parts)
            if combined:
                return DetailStrategyResult(strategy="search_content", content=combined[:500])
        except Exception:
            return None
        return None

    def _fetch_web_fallback(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            response = self.fetch(source_url, headers=self._build_headers(), timeout=15)
            text = self._extract_text_from_html(response.text)
            if text:
                return DetailStrategyResult(strategy="web_fallback", content=text[:500])
        except Exception:
            return None
        return None

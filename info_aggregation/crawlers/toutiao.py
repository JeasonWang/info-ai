"""
信息聚合系统 - 今日头条爬虫
爬取今日头条热点新闻，并深入爬取详情页获取完整内容
"""
import hashlib
import re
from datetime import datetime
from typing import Callable
from urllib.parse import quote

from .base import BaseCrawler
from services.collection.detail_pipeline import DetailStrategyResult, limit_detail_content, run_detail_pipeline


RenderedFetcher = Callable[[str], str]


class ToutiaoCrawler(BaseCrawler):
    """
    今日头条爬虫
    通过头条热点API获取热点新闻
    爬取频率：每30分钟一次
    """

    TREND_API = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    DETAIL_API = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    ARTICLE_API = "https://www.toutiao.com/article/{article_id}/"

    def __init__(self, rendered_fetcher: RenderedFetcher | None = None):
        super().__init__("toutiao", "今日头条")
        self.rendered_fetcher = rendered_fetcher

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
            # 如果当前片段只是已有标题的扩展版，去掉重复前缀，只保留新增信息。
            for existing in merged_parts:
                if normalized.startswith(existing):
                    normalized = normalized[len(existing):].lstrip("，。,:：;； ")
            if not normalized:
                continue
            # 过滤标题与摘要、摘要与正文之间的包含式重复，避免正文里反复出现同一句开头。
            if any(normalized in existing or existing in normalized for existing in merged_parts):
                continue
            merged_parts.append(normalized)
            seen.add(normalized)

        return " ".join(merged_parts).strip()

    def _clean_search_text(self, value: str) -> str:
        cleaned = re.sub(r"<[^>]+>", "", str(value or ""))
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _extract_image_url(self, image_value) -> str:
        if isinstance(image_value, dict):
            return str(image_value.get("url") or image_value.get("uri") or "").strip()
        return str(image_value or "").strip()

    def _has_meaningful_detail_fields(self, title: str, parts: list[str]) -> bool:
        normalized_title = re.sub(r"\s+", "", title or "")
        for part in parts:
            normalized_part = re.sub(r"\s+", "", str(part or ""))
            if not normalized_part:
                continue
            if normalized_title and normalized_part in {normalized_title, f"标签：{normalized_title}"}:
                continue
            if normalized_part.lower() in {"hot", "标签：hot"}:
                continue
            if len(normalized_part) >= 18:
                return True
        return False

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
                query_word = item.get("QueryWord", "")
                raw_hot_board_url = item.get("Url") or ""
                hot_board_url = f"https://www.toutiao.com/trending/{cluster_id}/" if cluster_id else raw_hot_board_url
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
                    "source_url": hot_board_url,
                    "event_time": datetime.now(),
                    "core_entity": title[:20],
                    "location": "",
                    "indicator_name": "",
                    "indicator_value": "",
                    "_cluster_id": cluster_id,
                    "_hot_desc": hot_desc,
                    "_label": label,
                    "_query_word": query_word,
                    "_hot_board_url": raw_hot_board_url or hot_board_url,
                    "_image_url": self._extract_image_url(item.get("Image")),
                    "_interest_category": item.get("InterestCategory") or [],
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
            result = self._run_detail_pipeline(item, candidates)
            if self._is_good_enough_without_render(result):
                return result

        search_content = self._fetch_search_content(item)
        if search_content:
            candidates.append(search_content)
            result = self._run_detail_pipeline(item, candidates)
            if self._is_good_enough_without_render(result):
                return result

        web_fallback = self._fetch_web_fallback(item)
        if web_fallback:
            candidates.append(web_fallback)
            result = self._run_detail_pipeline(item, candidates)
            if self._is_good_enough_without_render(result):
                return result

        rendered_content = self._fetch_rendered_content(item)
        if rendered_content:
            candidates.append(rendered_content)

        return self._run_detail_pipeline(item, candidates)

    def _run_detail_pipeline(self, item: dict, candidates: list[DetailStrategyResult]):
        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )

    def _is_good_enough_without_render(self, result) -> bool:
        """轻量详情已具备可分析上下文时，避免为热榜短内容继续启动浏览器。"""
        return result.status == "complete" or (result.status == "partial" and result.score >= 60)

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
            if combined and self._has_meaningful_detail_fields(item.get("title", ""), content_parts):
                return DetailStrategyResult(strategy="hot_board_detail", content=limit_detail_content(combined))
        except Exception:
            return None
        return None

    def _fetch_search_content(self, item: dict):
        word = str(item.get("_query_word") or item.get("title", "")).strip()
        if not word:
            return None

        try:
            search_url = f"https://www.toutiao.com/api/search/content/?keyword={quote(word)}&count=5"
            search_data = self.fetch_json(search_url, headers=self._build_detail_headers())
            search_items = search_data.get("data", [])
            merged_parts = []
            prefix_parts = []
            for raw_part in (item.get("_hot_desc", ""), item.get("_label", "")):
                part = self._clean_search_text(str(raw_part or ""))
                if not part:
                    continue
                if part == word or part in word or word in part:
                    continue
                prefix_parts.append(part)
            for search_item in search_items[:3]:
                for key in ("title", "abstract", "content"):
                    value = self._clean_search_text(search_item.get(key, ""))
                    if value:
                        merged_parts.append(value)
            combined = self._merge_distinct_parts(merged_parts, prefix=" ".join(str(part).strip() for part in prefix_parts if str(part).strip()))
            if combined:
                return DetailStrategyResult(strategy="search_content", content=limit_detail_content(combined))
        except Exception:
            return None
        return None

    def _fetch_rendered_content(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            rendered_text = self._render_page_text(source_url)
            cleaned = self._clean_rendered_text(rendered_text)
            if cleaned:
                title = str(item.get("title", "")).strip()
                if title and title not in cleaned:
                    cleaned = self._merge_distinct_parts([cleaned], prefix=title)
                return DetailStrategyResult(strategy="rendered_page", content=limit_detail_content(cleaned))
        except Exception:
            return None
        return None

    def _render_page_text(self, source_url: str) -> str:
        if self.rendered_fetcher:
            return self.rendered_fetcher(source_url)

        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            return ""

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="zh-CN",
                    viewport={"width": 1365, "height": 900},
                )
                page = context.new_page()
                # 头条文章页会持续发起埋点/推荐请求，等待 networkidle 容易超时；
                # DOM 就绪后短暂停顿更适合详情正文抽取。
                page.goto(source_url, wait_until="domcontentloaded", timeout=18000)
                page.wait_for_timeout(2500)
                return page.locator("body").inner_text(timeout=5000)
            finally:
                browser.close()

    def _clean_rendered_text(self, text: str) -> str:
        raw_lines = [re.sub(r"\s+", " ", raw_line).strip() for raw_line in str(text or "").splitlines()]
        compact_lines = [line for line in raw_lines if line]
        if "事件详情" in compact_lines:
            compact_lines = compact_lines[compact_lines.index("事件详情") + 1:]

        lines = []
        interaction_markers = {"分享", "评论", "赞", "查看更多"}
        exact_noise = {
            "您需要允许该网站执行 JavaScript",
            "登录",
            "注册",
            "打开今日头条",
            "今日头条",
            "广告",
            "关注",
            "相关内容",
        } | interaction_markers
        stop_patterns = ("网友讨论", "评论区", "相关推荐", "热门评论", "举报", "热门：", "TA的热门作品")
        for line in compact_lines:
            if any(pattern in line for pattern in stop_patterns):
                break
            if line in interaction_markers and lines:
                break
            if line in exact_noise:
                continue
            if "热门事件阅读量" in line:
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}", line):
                continue
            if re.search(r"(评论)?(分钟前|小时前|前天|昨天|刚刚)", line) and len(line) <= 35:
                continue
            if re.fullmatch(r"[+#]?\d+|[+#]\d+|[0-9]+\s*图", line):
                continue
            # 渲染页会包含作者、互动、频道导航等短文本；详情正文必须具备基本信息密度。
            if len(line) < 28:
                continue
            lines.append(line)
        return self._merge_distinct_parts(lines)

    def _fetch_web_fallback(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            response = self.fetch(source_url, headers=self._build_headers(), timeout=15)
            html = response.text
            match = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL | re.IGNORECASE)
            text = ""
            if match:
                text = self._extract_text_from_html(match.group(0))
            if not text:
                text = self._extract_text_from_html(html)
            if text:
                return DetailStrategyResult(strategy="web_fallback", content=limit_detail_content(text))
        except Exception:
            return None
        return None

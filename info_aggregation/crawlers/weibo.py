"""
信息聚合系统 - 微博热搜爬虫
爬取微博热搜榜，获取热点事件信息，并深入爬取详情页获取完整内容
"""
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

from .base import BaseCrawler
from services.detail_pipeline import DetailStrategyResult, limit_detail_content, run_detail_pipeline


class WeiboCrawler(BaseCrawler):
    """
    微博热搜爬虫
    通过微博移动端页面获取实时热点事件
    爬取频率：每30分钟一次
    """

    HOT_SEARCH_API = "https://weibo.com/ajax/side/hotSearch"
    MOBILE_HOT_API = "https://m.weibo.cn/api/container/getIndex?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot"
    HOT_BAND_API = "https://weibo.com/ajax/statuses/hot_band"

    def __init__(self):
        super().__init__("weibo", "微博")

    def _strip_env_quotes(self, value: str) -> str:
        if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
            return value[1:-1]
        return value

    def _get_env_value(self, name: str) -> str:
        value = os.getenv(name, "").strip()
        if value:
            return self._strip_env_quotes(value)

        candidates = [
            Path.cwd() / ".env",
            Path.cwd().parent / ".env",
            Path(__file__).resolve().parents[2] / ".env",
        ]
        for env_path in candidates:
            if not env_path.exists():
                continue
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or not stripped.startswith(f"{name}="):
                        continue
                    return self._strip_env_quotes(stripped.split("=", 1)[1].strip())
            except OSError:
                continue
        return ""

    def _get_weibo_cookie(self) -> str:
        return self._get_env_value("WEIBO_COOKIE")

    def _build_weibo_headers(self, referer: str, accept_json: bool = False) -> dict:
        headers = self._build_headers()
        headers["Referer"] = referer
        if accept_json:
            headers["Accept"] = "application/json, text/plain, */*"
            headers["X-Requested-With"] = "XMLHttpRequest"
        cookie = self._get_weibo_cookie()
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def crawl(self) -> list:
        results = []
        try:
            results = self._crawl_mobile_api()
            if results:
                return results
        except Exception:
            pass

        try:
            results = self._crawl_hot_band()
            if results:
                return results
        except Exception:
            pass

        try:
            results = self._crawl_web_page()
            if results:
                return results
        except Exception as e:
            self.logger.error(f"微博爬取异常: {e}")
        return results

    def _crawl_mobile_api(self) -> list:
        headers = self._build_weibo_headers("https://m.weibo.cn/", accept_json=True)
        data = self.fetch_json(self.MOBILE_HOT_API, headers=headers)
        cards = data.get("data", {}).get("cards", [])
        results = []
        for card in cards:
            card_group = card.get("card_group", [])
            for item in card_group:
                desc = item.get("desc", "")
                title = desc.strip() if desc else ""
                if not title:
                    continue
                source_id = hashlib.md5(f"weibo_{title}".encode()).hexdigest()[:16]
                results.append({
                    "source_id": source_id,
                    "title": title[:40],
                    "content": title[:500],
                    "source_url": f"https://s.weibo.com/weibo?q=%23{title}%23",
                    "event_time": datetime.now(),
                    "core_entity": title[:20],
                    "location": "",
                    "indicator_name": "",
                    "indicator_value": "",
                    "_allow_title_only": True,
                })
            if len(results) >= 20:
                break
        return results[:20]

    def _crawl_hot_band(self) -> list:
        headers = self._build_weibo_headers("https://weibo.com/", accept_json=True)
        data = self.fetch_json(self.HOT_BAND_API, headers=headers)
        band_list = data.get("data", {}).get("band_list", [])
        results = []
        for band in band_list[:20]:
            word = band.get("word", "").strip()
            if not word:
                continue
            note = band.get("note", word)
            raw_text = band.get("raw_text", "")
            desc = band.get("desc", "")
            label_name = band.get("label_name", "")
            category = band.get("category", "")
            rank = band.get("rank", "")
            num = band.get("num", "")
            content_parts = [note]
            if raw_text and raw_text != note:
                content_parts.append(raw_text)
            if desc and desc != note and desc != raw_text:
                content_parts.append(desc)
            if label_name:
                content_parts.append(f"热榜标签：{label_name}")
            if category:
                content_parts.append(f"热榜分类：{category}")
            if rank != "":
                content_parts.append(f"当前排名：{rank}")
            if num:
                content_parts.append(f"热度值：{num}")
            content = "。".join(content_parts)
            source_id = hashlib.md5(f"weibo_{word}".encode()).hexdigest()[:16]
            results.append({
                "source_id": source_id,
                "title": word[:40],
                "content": content[:500],
                "source_url": f"https://s.weibo.com/weibo?q=%23{word}%23",
                "event_time": datetime.now(),
                "core_entity": word[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
                "_allow_title_only": True,
            })
        return results

    def _crawl_web_page(self) -> list:
        headers = self._build_weibo_headers("https://s.weibo.com/")
        url = "https://s.weibo.com/top/summary"
        response = self.fetch(url, headers=headers)
        html = response.text
        results = []
        pattern = r'<td class="td-02">\s*<a[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for word in matches[:20]:
            word = word.strip()
            if not word:
                continue
            source_id = hashlib.md5(f"weibo_{word}".encode()).hexdigest()[:16]
            results.append({
                "source_id": source_id,
                "title": word[:40],
                "content": word[:500],
                "source_url": f"https://s.weibo.com/weibo?q=%23{word}%23",
                "event_time": datetime.now(),
                "core_entity": word[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
                "_allow_title_only": True,
            })
        return results

    def fetch_detail(self, source_url: str, item: dict) -> str:
        result = self.resolve_detail(item)
        return result.content

    def resolve_detail(self, item: dict):
        candidates = []

        topic_search = self._fetch_topic_search(item)
        if topic_search:
            candidates.append(topic_search)
            topic_result = self._run_detail_pipeline(item, candidates)
            if self._is_good_enough_without_mobile_search(topic_result):
                return topic_result

        # 登录态可用时，移动搜索通常能拿到多条真实微博正文，比热榜上下文更有分析价值。
        if self._get_weibo_cookie():
            mobile_search = self._fetch_mobile_search(item)
            if mobile_search:
                mobile_result = self._run_detail_pipeline(item, [mobile_search])
                if mobile_result.status in {"complete", "partial"} and mobile_result.content_length >= 120:
                    return mobile_result
                candidates.append(mobile_search)

        hot_band_context = self._fetch_hot_band_context(item)
        if hot_band_context:
            candidates.append(hot_band_context)
            hot_band_result = self._run_detail_pipeline(item, candidates)
            if self._is_good_enough_without_mobile_search(hot_band_result):
                return hot_band_result

        if not self._get_weibo_cookie():
            mobile_search = self._fetch_mobile_search(item)
            if mobile_search:
                candidates.append(mobile_search)

        web_fallback = self._fetch_web_fallback(item)
        if web_fallback:
            candidates.append(web_fallback)

        return self._run_detail_pipeline(item, candidates)

    def _run_detail_pipeline(self, item: dict, candidates: list[DetailStrategyResult]):
        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )

    def _is_good_enough_without_mobile_search(self, result) -> bool:
        return result.status in {"complete", "partial"}

    def _clean_weibo_text(self, text: str) -> str:
        """清洗微博正文文本，去掉标签和多余空白。"""
        cleaned = re.sub(r"<[^>]+>", "", text or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _merge_distinct_parts(self, parts: list[str], prefix: str = "") -> str:
        """按顺序合并多段正文，并去掉重复内容。"""
        merged_parts = []
        seen = set()

        if prefix:
            normalized_prefix = prefix.strip()
            if normalized_prefix:
                merged_parts.append(normalized_prefix)
                seen.add(normalized_prefix)

        for part in parts:
            normalized = part.strip()
            if not normalized or normalized in seen:
                continue
            merged_parts.append(normalized)
            seen.add(normalized)

        return " ".join(merged_parts).strip()

    def _extract_mobile_mblog_parts(self, mblog: dict) -> list[str]:
        """提取微博移动端卡片里的主贴、长文和转发补充正文。"""
        parts = []

        text = self._clean_weibo_text(mblog.get("text", ""))
        if text:
            parts.append(text.replace("全文", "").strip())

        long_text = mblog.get("longText", {}) if isinstance(mblog.get("longText"), dict) else {}
        long_text_content = self._clean_weibo_text(long_text.get("longTextContent", ""))
        if long_text_content:
            parts.append(long_text_content)

        retweeted_status = mblog.get("retweeted_status", {})
        if isinstance(retweeted_status, dict):
            retweet_text = self._clean_weibo_text(retweeted_status.get("text", ""))
            if retweet_text:
                parts.append(retweet_text)

            retweet_long_text = retweeted_status.get("longText", {})
            if isinstance(retweet_long_text, dict):
                retweet_long_text_content = self._clean_weibo_text(retweet_long_text.get("longTextContent", ""))
                if retweet_long_text_content:
                    parts.append(retweet_long_text_content)

        return parts

    def _extract_status_parts(self, status: dict) -> list[str]:
        """统一提取微博状态对象里的正文、长文和转发补充，供多种详情策略复用。"""
        if not isinstance(status, dict):
            return []
        return self._extract_mobile_mblog_parts(status)

    def _extract_web_fallback_content(self, html: str, title: str) -> str:
        """
        从微博网页搜索结果中优先抽取正文块，避免把整页导航噪声当成详情内容。
        """
        if self._looks_like_weibo_template_shell(html):
            return ""

        block_patterns = [
            r"<article[^>]*>(.*?)</article>",
            r'<div[^>]*class="[^"]*(?:card-wrap|content|article|detail|body)[^"]*"[^>]*>(.*?)</div>',
            r"<main[^>]*>(.*?)</main>",
        ]

        cleaned_blocks = []
        for pattern in block_patterns:
            for match in re.findall(pattern, html, re.DOTALL | re.IGNORECASE):
                cleaned = self._clean_weibo_text(match)
                if cleaned:
                    cleaned_blocks.append(cleaned)

        # 优先选择包含标题且长度足够的正文块，减少导航、页头、推荐区对兜底结果的污染。
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

    def _looks_like_weibo_template_shell(self, html: str) -> bool:
        shell_markers = (
            "{{ model_title.title }}",
            "{{ item.user_name }}",
            "快速概览(Qwen3",
            "深度思考(DS-R1",
            "问题分析中",
            "答案整理中",
        )
        return any(marker in (html or "") for marker in shell_markers)

    def _fetch_topic_search(self, item: dict):
        headers = self._build_weibo_headers("https://weibo.com/", accept_json=True)
        word = item.get("title", "")
        if not word:
            return None

        try:
            search_detail = f"https://weibo.com/ajax/search/topic?query={word}&page=1"
            data = self.fetch_json(search_detail, headers=headers)
            statuses = data.get("data", {}).get("statuses", [])
            text_parts = []
            for status in statuses[:5]:
                # 话题搜索结果里也可能包含长文和转发补充，不能只拿表层短文本。
                text_parts.extend(self._extract_status_parts(status))
            combined = self._merge_distinct_parts(text_parts)
            if combined:
                return DetailStrategyResult(strategy="topic_search", content=combined)
        except Exception:
            return None
        return None

    def _fetch_hot_band_context(self, item: dict):
        headers = self._build_weibo_headers("https://weibo.com/", accept_json=True)
        word = item.get("title", "").strip()
        if not word:
            return None

        try:
            data = self.fetch_json(self.HOT_BAND_API, headers=headers)
            band_list = data.get("data", {}).get("band_list", [])
            for band in band_list:
                if band.get("word", "").strip() != word:
                    continue
                content_parts = []
                for key in ("note", "raw_text", "desc"):
                    value = str(band.get(key, "")).strip()
                    if value and value not in content_parts:
                        content_parts.append(value)
                label_name = str(band.get("label_name", "")).strip()
                category = str(band.get("category", "")).strip()
                rank = str(band.get("rank", "")).strip()
                num = str(band.get("num", "")).strip()
                if label_name:
                    content_parts.append(f"热榜标签：{label_name}")
                if category:
                    content_parts.append(f"热榜分类：{category}")
                if rank:
                    content_parts.append(f"当前排名：{rank}")
                if num:
                    content_parts.append(f"热度值：{num}")
                # 热榜上下文通常偏短，补上标题作为事件锚点，减少被判成弱相关或部分详情。
                combined = self._merge_distinct_parts(content_parts, prefix=word)
                if combined and len(combined) < 80:
                    combined = f"微博热搜 {word} 正在持续发酵，当前背景包括：{'；'.join(content_parts)}。"
                if combined:
                    return DetailStrategyResult(strategy="hot_band_context", content=combined)
        except Exception:
            return None
        return None

    def _fetch_mobile_search(self, item: dict):
        headers = self._build_weibo_headers("https://m.weibo.cn/", accept_json=True)
        word = item.get("title", "")
        if not word:
            return None

        try:
            mobile_url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{word}"
            data = self.fetch_json(mobile_url, headers=headers)
            cards = data.get("data", {}).get("cards", [])
            text_parts = []
            for card in cards[:5]:
                mblog = card.get("mblog", {})
                if not mblog:
                    continue
                # 移动端结果优先拼接长文和转发补充，避免只拿到“全文”前的残缺摘要。
                text_parts.extend(self._extract_mobile_mblog_parts(mblog))
            combined = self._merge_distinct_parts(text_parts)
            if combined:
                return DetailStrategyResult(strategy="mobile_search", content=combined)
        except Exception:
            return None
        return None

    def _fetch_web_fallback(self, item: dict):
        try:
            headers = self._build_weibo_headers("https://weibo.com/", accept_json=True)

            word = item.get("title", "")
            if not word:
                return None
            response = self.fetch(f"https://s.weibo.com/weibo?q={word}", headers=headers)
            # 网页兜底只抽正文相关区块，不直接使用整页文本，避免把导航壳页面误当成详情。
            text = self._extract_web_fallback_content(response.text, word)
            if text:
                return DetailStrategyResult(strategy="web_fallback", content=limit_detail_content(text))
            return None
        except Exception as e:
            self.logger.warning(f"微博详情爬取失败: {e}")
            return None

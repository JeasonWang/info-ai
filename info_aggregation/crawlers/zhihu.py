"""
信息聚合系统 - 知乎爬虫
爬取知乎AI/大模型相关热门话题，并深入爬取详情页获取完整内容
"""
import hashlib
import html
import re
from datetime import datetime
from typing import Callable
from urllib.parse import quote

from .base import BaseCrawler
from services.credential_provider import get_credential
from services.detail_pipeline import DetailStrategyResult, limit_detail_content, run_detail_pipeline


RenderedFetcher = Callable[[str], str]


class ZhihuCrawler(BaseCrawler):
    """
    知乎爬虫
    通过知乎网页端获取热门话题
    爬取频率：每2小时一次
    """

    HOT_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20"
    HOT_SEARCH_API = "https://www.zhihu.com/api/v4/search/hot_search"
    SEARCH_API = "https://www.zhihu.com/api/v4/search_v3?t=general&q={query}&correction=1&offset=0&limit=5"
    HOT_URL = "https://www.zhihu.com/hot"
    ANSWER_INCLUDE = "data[*].content,voteup_count,comment_count,created_time,updated_time,author"
    QUESTION_API = (
        "https://www.zhihu.com/api/v4/questions/{question_id}/answers"
        "?limit=5&sort_by=default&include={include}"
    )

    def __init__(self, rendered_fetcher: RenderedFetcher | None = None):
        super().__init__("zhihu", "知乎")
        self.rendered_fetcher = rendered_fetcher

    def _merge_distinct_parts(self, parts: list[str], prefix: str = "") -> str:
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
            if any(normalized in existing or existing in normalized for existing in merged_parts):
                continue
            merged_parts.append(normalized)
            seen.add(normalized)
        return " ".join(merged_parts).strip()

    def _normalize_html_text(self, value: str) -> str:
        value = re.sub(r"<[^>]+>", " ", str(value or ""))
        value = html.unescape(value)
        value = re.sub(r"\s+", " ", value).strip()
        return re.sub(r"\s+([，。！？；：、,.!?;:])", r"\1", value)

    def _build_zhihu_headers(self, referer: str = "https://www.zhihu.com/") -> dict:
        headers = self._build_headers()
        headers["Referer"] = referer
        headers["Accept"] = "application/json, text/plain, */*" if "/api/" in referer else headers["Accept"]
        headers["x-api-version"] = "3.0.91"
        headers["x-requested-with"] = "fetch"
        cookie = self._get_zhihu_cookie()
        if cookie:
            headers["Cookie"] = cookie
        zse_93 = get_credential("ZHIHU_ZSE_93")
        zse_96 = get_credential("ZHIHU_ZSE_96")
        if zse_93:
            headers["x-zse-93"] = zse_93
        if zse_96:
            headers["x-zse-96"] = zse_96
        return headers

    def _get_zhihu_cookie(self) -> str:
        return get_credential("ZHIHU_COOKIE")

    def _build_source_id(self, source_url: str, fallback_title: str) -> str:
        source_key = source_url or f"hot_search_{fallback_title}"
        return hashlib.md5(f"zhihu_{source_key}".encode()).hexdigest()[:16]

    def _parse_cookie_jar(self, raw_cookie: str) -> list[dict]:
        cookies = []
        for part in str(raw_cookie or "").split(";"):
            if "=" not in part:
                continue
            name, value = part.strip().split("=", 1)
            if not name:
                continue
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".zhihu.com",
                "path": "/",
            })
        return cookies

    def crawl(self) -> list:
        results = []
        try:
            results = self._crawl_hot_search_api()
            if results:
                return results
        except Exception:
            pass

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
            self.logger.error(f"知乎爬取异常: {e}")
        return results

    def _crawl_hot_search_api(self) -> list:
        headers = self._build_zhihu_headers("https://www.zhihu.com/hot")
        data = self.fetch_json(self.HOT_SEARCH_API, headers=headers)
        words = self._extract_hot_search_words(data)
        results = []
        seen = set()
        for word in words[:20]:
            title = str(
                word.get("display_query")
                or word.get("real_query")
                or word.get("query")
                or word.get("word")
                or ""
            ).strip()
            if not title or title in seen:
                continue
            seen.add(title)
            detail_text = str(word.get("detail_text") or word.get("desc") or "").strip()
            hot_show = str(word.get("hot_show") or word.get("hot") or "").strip()
            enriched = self._enrich_hot_search_item(title)
            source_url = enriched.get("source_url") or f"https://www.zhihu.com/search?type=content&q={quote(title)}"
            item = {
                "source_id": self._build_source_id(source_url, title),
                "title": enriched.get("title", title)[:80],
                "content": detail_text or title,
                "source_url": source_url,
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "hot_show" if hot_show else "",
                "indicator_value": hot_show,
                "_query_word": title,
            }
            if enriched.get("content"):
                item["content"] = enriched["content"]
                item["_search_content"] = enriched["content"]
            if enriched.get("content_type"):
                item["_content_type"] = enriched["content_type"]
            results.append(item)
        return results

    def _extract_hot_search_words(self, data: dict) -> list[dict]:
        if isinstance(data.get("hot_search_queries"), list):
            return data["hot_search_queries"]
        if isinstance(data.get("top_search"), dict):
            words = data["top_search"].get("words")
            if isinstance(words, list):
                return words
        if isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data.get("hot_search"), list):
            return data["hot_search"]
        return []

    def _enrich_hot_search_item(self, query: str) -> dict:
        try:
            search_url = self.SEARCH_API.format(query=quote(query))
            referer = f"https://www.zhihu.com/search?type=content&q={quote(query)}"
            data = self.fetch_json(search_url, headers=self._build_zhihu_headers(referer))
        except Exception as e:
            self.logger.warning(f"知乎热搜二次搜索失败: {e}")
            return {}

        for entry in data.get("data", []):
            candidate = self._extract_search_candidate(entry)
            if candidate:
                return candidate
        return {}

    def _extract_search_candidate(self, entry: dict) -> dict:
        obj = entry.get("object") if isinstance(entry, dict) else None
        if not isinstance(obj, dict):
            return {}

        nested = obj.get("description", {}).get("object") if isinstance(obj.get("description"), dict) else None
        if isinstance(nested, dict):
            candidate = self._build_candidate_from_search_object(nested)
            if candidate:
                return candidate

        candidate = self._build_candidate_from_search_object(obj)
        if candidate:
            return candidate

        for content_item in obj.get("content_items", []) if isinstance(obj.get("content_items"), list) else []:
            content_obj = content_item.get("object") if isinstance(content_item, dict) else None
            candidate = self._build_candidate_from_search_object(content_obj if isinstance(content_obj, dict) else {})
            if candidate:
                return candidate
        return {}

    def _build_candidate_from_search_object(self, obj: dict) -> dict:
        content_type = obj.get("type")
        item_id = str(obj.get("id") or "").strip()
        title = self._normalize_html_text(str(obj.get("title") or ""))
        description = self._normalize_html_text(str(obj.get("description") or obj.get("excerpt") or ""))
        content = self._normalize_html_text(str(obj.get("content") or ""))
        merged_content = self._merge_distinct_parts([description, content], prefix=title)

        source_url = ""
        api_url = str(obj.get("url") or "")
        if content_type == "question" and item_id:
            source_url = f"https://www.zhihu.com/question/{item_id}"
        elif content_type == "article" and item_id:
            source_url = f"https://zhuanlan.zhihu.com/p/{item_id}"
        elif api_url:
            source_url = api_url.replace("https://api.zhihu.com/questions/", "https://www.zhihu.com/question/")
            source_url = source_url.replace("https://api.zhihu.com/articles/", "https://zhuanlan.zhihu.com/p/")

        if not source_url or not title:
            return {}
        return {
            "title": title,
            "content": merged_content,
            "source_url": source_url,
            "content_type": content_type,
        }

    def _crawl_api(self) -> list:
        headers = self._build_zhihu_headers("https://www.zhihu.com/hot")
        headers["Authorization"] = "Bearer "
        data = self.fetch_json(self.HOT_API, headers=headers)
        items = data.get("data", [])
        results = []
        for item in items[:20]:
            target = item.get("target", {})
            title = target.get("title", "").strip()
            if not title:
                continue
            question_id = target.get("id", "")
            source_id = hashlib.md5(f"zhihu_{question_id}".encode()).hexdigest()[:16]
            excerpt = target.get("excerpt", title)[:500]
            results.append({
                "source_id": source_id,
                "title": title[:40],
                "content": excerpt,
                "source_url": f"https://www.zhihu.com/question/{question_id}",
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
        return results

    def _crawl_web_page(self) -> list:
        headers = self._build_zhihu_headers("https://www.zhihu.com/")
        response = self.fetch(self.HOT_URL, headers=headers)
        html = response.text
        results = []
        question_pattern = re.findall(
            r'<a[^>]*href="/question/(\d+)"[^>]*class="[^"]*Title[^"]*"[^>]*>([^<]+)</a>',
            html, re.DOTALL
        )
        if not question_pattern:
            question_pattern = re.findall(
                r'href="/question/(\d+)"[^>]*>([^<]{4,}?)</a>',
                html, re.DOTALL
            )
        seen = set()
        for question_id, title in question_pattern:
            title = title.strip()
            if not title or question_id in seen:
                continue
            seen.add(question_id)
            source_id = hashlib.md5(f"zhihu_{question_id}".encode()).hexdigest()[:16]
            results.append({
                "source_id": source_id,
                "title": title[:40],
                "content": title[:500],
                "source_url": f"https://www.zhihu.com/question/{question_id}",
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
            })
            if len(results) >= 20:
                break
        return results

    def fetch_detail(self, source_url: str, item: dict) -> str:
        return self.resolve_detail(item).content

    def resolve_detail(self, item: dict):
        candidates = []

        embedded_detail = self._fetch_embedded_search_detail(item)
        if embedded_detail:
            candidates.append(embedded_detail)
            embedded_result = run_detail_pipeline(
                title=item.get("title", ""),
                list_content=item.get("content", ""),
                strategy_results=candidates,
                channel_code=self.channel_code,
            )
            if self._is_good_enough_without_render(embedded_result):
                return embedded_result

        answer_api_detail = self._fetch_answer_api_detail(item)
        if answer_api_detail:
            candidates.append(answer_api_detail)

        early_result = run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )
        if self._is_good_enough_without_render(early_result):
            return early_result

        web_detail = self._fetch_web_detail(item)
        if web_detail:
            candidates.append(web_detail)
            web_result = run_detail_pipeline(
                title=item.get("title", ""),
                list_content=item.get("content", ""),
                strategy_results=candidates,
                channel_code=self.channel_code,
            )
            if self._is_good_enough_without_render(web_result):
                return web_result

        rendered_detail = self._fetch_rendered_detail(item)
        if rendered_detail:
            candidates.append(rendered_detail)

        web_fallback = self._fetch_web_fallback(item)
        if web_fallback:
            candidates.append(web_fallback)

        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )

    def _is_good_enough_without_render(self, result) -> bool:
        return result.status in {"complete", "partial"}

    def _fetch_embedded_search_detail(self, item: dict):
        content = self._normalize_html_text(str(item.get("_search_content") or ""))
        if len(content) >= 40:
            return DetailStrategyResult(strategy="search_embedded", content=limit_detail_content(content))
        return None

    def _fetch_answer_api_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url or "/question/" not in source_url:
            return None

        try:
            headers = self._build_zhihu_headers("https://www.zhihu.com/api/")

            question_id = source_url.split("/question/")[-1].split("/")[0].split("?")[0]
            answers_api = self.QUESTION_API.format(
                question_id=question_id,
                include=quote(self.ANSWER_INCLUDE, safe=""),
            )
            data = self.fetch_json(answers_api, headers=headers)
            answers = data.get("data", [])
            if not answers:
                return None

            segments = []
            seen_segments = set()
            ranked_answers = sorted(
                answers,
                key=lambda answer: (
                    int(answer.get("voteup_count") or 0),
                    len(str(answer.get("content") or answer.get("excerpt") or "")),
                ),
                reverse=True,
            )
            for answer in ranked_answers[:5]:
                content = str(answer.get("content", "")).strip()
                if not content:
                    content = str(answer.get("excerpt", "")).strip()
                if not content:
                    continue
                content = self._normalize_answer_text(content)
                if len(content) < 30:
                    continue
                if content and content not in seen_segments:
                    seen_segments.add(content)
                    segments.append(content)
                if len(segments) >= 3:
                    break

            merged = " ".join(segments).strip()
            if len(merged) >= 20:
                return DetailStrategyResult(strategy="answer_api", content=limit_detail_content(merged))
        except Exception as e:
            self.logger.warning(f"知乎回答API解析失败: {e}")

        return None

    def _normalize_answer_text(self, content: str) -> str:
        content = re.sub(r"<[^>]+>", "", content)
        content = html.unescape(content)
        content = re.sub(r"\s+", " ", content).strip()
        return content

    def _fetch_web_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_zhihu_headers("https://www.zhihu.com/")
            response = self.fetch(source_url, headers=headers)
            html = response.text
            match = re.search(r'class="RichContent-inner"[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                content = re.sub(r"<[^>]+>", "", content)
                content = re.sub(r"\s+", " ", content).strip()
                if len(content) >= 20:
                    return DetailStrategyResult(strategy="fetch_detail", content=limit_detail_content(content))
        except Exception as e:
            self.logger.warning(f"知乎页面正文解析失败: {e}")

        return None

    def _fetch_web_fallback(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_zhihu_headers("https://www.zhihu.com/")
            response = self.fetch(source_url, headers=headers)
            text = self._extract_text_from_html(response.text)
            if text and len(text) >= 20:
                return DetailStrategyResult(strategy="web_fallback", content=limit_detail_content(text))
        except Exception as e:
            self.logger.warning(f"知乎网页兜底解析失败: {e}")

        return None

    def _fetch_rendered_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            rendered_text = self._render_page_text(source_url)
            cleaned = self._clean_rendered_text(rendered_text, item.get("title", ""))
            if cleaned:
                return DetailStrategyResult(strategy="rendered_question", content=limit_detail_content(cleaned))
        except Exception as e:
            self.logger.warning(f"知乎渲染详情解析失败: {e}")
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
                cookie = self._get_zhihu_cookie()
                if cookie:
                    context.add_cookies(self._parse_cookie_jar(cookie))
                page = context.new_page()
                page.goto(source_url, wait_until="domcontentloaded", timeout=18000)
                page.wait_for_timeout(2500)
                return page.locator("body").inner_text(timeout=5000)
            finally:
                browser.close()

    def _clean_rendered_text(self, text: str, title: str = "") -> str:
        raw_lines = [re.sub(r"\s+", " ", line).strip() for line in str(text or "").splitlines()]
        compact_lines = [line for line in raw_lines if line]

        lines = []
        exact_noise = {
            "知乎",
            "首页",
            "会员",
            "发现",
            "等你来答",
            "登录",
            "注册",
            "打开知乎App",
            "默认排序",
            "添加评论",
            "分享",
            "收藏",
            "喜欢",
            "收起",
            "展开阅读全文",
        }
        stop_patterns = (
            "添加评论",
            "相关推荐",
            "更多回答",
            "被以下专题收录",
            "还没有评论",
            "登录后你可以",
        )
        for line in compact_lines:
            if any(pattern in line for pattern in stop_patterns):
                break
            if line in exact_noise:
                continue
            if "验证码登录" in line or "扫码登录" in line or "登录/注册" in line:
                return ""
            if re.fullmatch(r"\d+\s*(个回答|条评论|人赞同了该回答|赞同)", line):
                continue
            if re.search(r"(编辑于|发布于|更新于)\s*\d{4}-\d{2}-\d{2}", line):
                continue
            if len(line) < 28 and line != title:
                continue
            lines.append(line)

        merged = self._merge_distinct_parts(lines, prefix=title if title else "")
        return merged

"""
信息聚合系统 - 知乎爬虫
爬取知乎AI/大模型相关热门话题，并深入爬取详情页获取完整内容
"""
import hashlib
import re
from datetime import datetime

from .base import BaseCrawler
from services.detail_pipeline import DetailStrategyResult, run_detail_pipeline


class ZhihuCrawler(BaseCrawler):
    """
    知乎爬虫
    通过知乎网页端获取热门话题
    爬取频率：每2小时一次
    """

    HOT_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20"
    HOT_URL = "https://www.zhihu.com/hot"
    QUESTION_API = "https://www.zhihu.com/api/v4/questions/{question_id}/answers?limit=3&sort_by=default"

    def __init__(self):
        super().__init__("zhihu", "知乎")

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
            self.logger.error(f"知乎爬取异常: {e}")
        return results

    def _crawl_api(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.zhihu.com/hot"
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
        headers = self._build_headers()
        headers["Referer"] = "https://www.zhihu.com/"
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

        answer_api_detail = self._fetch_answer_api_detail(item)
        if answer_api_detail:
            candidates.append(answer_api_detail)

        web_detail = self._fetch_web_detail(item)
        if web_detail:
            candidates.append(web_detail)

        web_fallback = self._fetch_web_fallback(item)
        if web_fallback:
            candidates.append(web_fallback)

        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
        )

    def _fetch_answer_api_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url or "/question/" not in source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.zhihu.com/"
            headers["Accept"] = "application/json, text/plain, */*"

            question_id = source_url.split("/question/")[-1].split("/")[0].split("?")[0]
            answers_api = self.QUESTION_API.format(question_id=question_id)
            data = self.fetch_json(answers_api, headers=headers)
            answers = data.get("data", [])
            if not answers:
                return None

            segments = []
            seen_segments = set()
            for answer in answers[:3]:
                content = str(answer.get("content", "")).strip()
                if not content:
                    content = str(answer.get("excerpt", "")).strip()
                if not content:
                    continue
                content = self._normalize_answer_text(content)
                if content and content not in seen_segments:
                    seen_segments.add(content)
                    segments.append(content)

            merged = " ".join(segments).strip()
            if len(merged) >= 20:
                return DetailStrategyResult(strategy="answer_api", content=merged[:500])
        except Exception as e:
            self.logger.warning(f"知乎回答API解析失败: {e}")

        return None

    def _normalize_answer_text(self, content: str) -> str:
        content = re.sub(r"<[^>]+>", "", content)
        content = re.sub(r"\s+", " ", content).strip()
        return content

    def _fetch_web_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.zhihu.com/"
            response = self.fetch(source_url, headers=headers)
            html = response.text
            match = re.search(r'class="RichContent-inner"[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                content = re.sub(r"<[^>]+>", "", content)
                content = re.sub(r"\s+", " ", content).strip()
                if len(content) >= 20:
                    return DetailStrategyResult(strategy="fetch_detail", content=content[:500])
        except Exception as e:
            self.logger.warning(f"知乎页面正文解析失败: {e}")

        return None

    def _fetch_web_fallback(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None

        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.zhihu.com/"
            response = self.fetch(source_url, headers=headers)
            text = self._extract_text_from_html(response.text)
            if text and len(text) >= 20:
                return DetailStrategyResult(strategy="web_fallback", content=text[:500])
        except Exception as e:
            self.logger.warning(f"知乎网页兜底解析失败: {e}")

        return None

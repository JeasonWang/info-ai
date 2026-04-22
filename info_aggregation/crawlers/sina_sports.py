"""
信息聚合系统 - 新浪体育爬虫。

新浪体育首页信息量很大，但混有彩票、中奖、投注分析等内容。
本爬虫优先抽取 sports.sina.com.cn 下的新闻正文链接，并过滤明显彩票内容。
"""
import re

from .base import BaseCrawler
from .sports_utils import (
    clean_html_text,
    extract_article_text,
    infer_datetime_from_url,
    is_useful_sports_title,
    normalize_url,
    stable_source_id,
)


class SinaSportsCrawler(BaseCrawler):
    """新浪体育爬虫。"""

    HOME_URL = "https://sports.sina.com.cn/"
    DETAIL_PATTERNS = [
        r'<div[^>]+id=["\']artibody["\'][^>]*>(.*?)</div>',
        r'<div[^>]+class=["\'][^"\']*article[^"\']*["\'][^>]*>(.*?)</div>',
        r'<div[^>]+class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
        r"<article[^>]*>(.*?)</article>",
    ]

    def __init__(self):
        super().__init__("sina_sports", "新浪体育")

    def crawl(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.sina.com.cn/"
        response = self.fetch(self.HOME_URL, headers=headers)
        return self._parse_home_page(self._get_response_text(response))

    def _get_response_text(self, response) -> str:
        """修正新浪页面常见的 GBK/UTF-8 编码识别问题，避免中文乱码入库。"""
        response.encoding = getattr(response, "apparent_encoding", None) or getattr(response, "encoding", None) or "utf-8"
        return response.text

    def _parse_home_page(self, html_text: str) -> list:
        """从新浪体育首页抽取新闻条目。"""
        link_pattern = re.findall(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html_text or "",
            re.DOTALL | re.IGNORECASE,
        )
        results = []
        seen_urls = set()

        for raw_url, raw_title in link_pattern:
            source_url = normalize_url(self.HOME_URL, raw_url)
            title = clean_html_text(raw_title)
            if not self._is_supported_url(source_url) or not is_useful_sports_title(title):
                continue
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            results.append(self._build_item(title, source_url))
            if len(results) >= 20:
                break
        return results

    def _is_supported_url(self, source_url: str) -> bool:
        """只保留新浪体育正文页，跳过彩票频道、图集和外链。"""
        if not source_url.startswith("https://sports.sina.com.cn/"):
            return False
        if "/l/" in source_url or "lottery" in source_url or "slide." in source_url:
            return False
        return source_url.endswith(".shtml") and "/20" in source_url

    def _build_item(self, title: str, source_url: str) -> dict:
        return {
            "source_id": stable_source_id(self.channel_code, source_url),
            "title": title[:40],
            "content": f"{title}。来自新浪体育的赛事与体育新闻，后续将持续跟进比赛结果和相关动态。"[:500],
            "source_url": source_url,
            "event_time": infer_datetime_from_url(source_url),
            "core_entity": title[:20],
            "location": "",
            "indicator_name": "",
            "indicator_value": "",
        }

    def fetch_detail(self, source_url: str, item: dict) -> str:
        try:
            headers = self._build_headers()
            headers["Referer"] = self.HOME_URL
            response = self.fetch(source_url, headers=headers)
            content = extract_article_text(self._get_response_text(response), self.DETAIL_PATTERNS)
            if content:
                return content
            return item.get("content", "")
        except Exception as exc:
            self.logger.warning(f"新浪体育详情爬取失败: {exc}")
            return ""

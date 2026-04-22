"""
信息聚合系统 - 央视体育网爬虫。

采集策略：
1. 从央视体育首页抽取新闻/视频链接；
2. 过滤导航、专题入口和过短标题；
3. 进入详情页提取正文或摘要，尽量避免只保存标题。
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


class CctvSportsCrawler(BaseCrawler):
    """央视体育网爬虫。"""

    HOME_URL = "https://sports.cctv.com/"
    DETAIL_PATTERNS = [
        r'<div[^>]+class=["\'][^"\']*content_area[^"\']*["\'][^>]*>(.*?)</div>',
        r'<div[^>]+class=["\'][^"\']*cnt_bd[^"\']*["\'][^>]*>(.*?)</div>',
        r'<div[^>]+class=["\'][^"\']*text_area[^"\']*["\'][^>]*>(.*?)</div>',
        r"<article[^>]*>(.*?)</article>",
    ]

    def __init__(self):
        super().__init__("cctv_sports", "央视体育网")

    def crawl(self) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.cctv.com/"
        response = self.fetch(self.HOME_URL, headers=headers)
        return self._parse_home_page(self._get_response_text(response))

    def _get_response_text(self, response) -> str:
        """按页面声明或探测结果修正编码，避免中文乱码入库。"""
        if getattr(response, "encoding", "") in ("ISO-8859-1", None, ""):
            response.encoding = getattr(response, "apparent_encoding", None) or "utf-8"
        return response.text

    def _parse_home_page(self, html_text: str) -> list:
        """从首页 HTML 中抽取体育新闻条目。"""
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
        """只保留央视体育图文正文页，跳过短视频页和导航专题页。"""
        if not source_url.startswith("https://sports.cctv.com/"):
            return False
        return "/20" in source_url and "ARTI" in source_url

    def _build_item(self, title: str, source_url: str) -> dict:
        return {
            "source_id": stable_source_id(self.channel_code, source_url),
            "title": title[:40],
            "content": f"{title}。来自央视体育网的体育新闻，后续将持续跟进赛事进展和相关报道。"[:500],
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
            return ""
        except Exception as exc:
            self.logger.warning(f"央视体育详情爬取失败: {exc}")
            return ""

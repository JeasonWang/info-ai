"""
信息聚合系统 - 博客园爬虫
爬取博客园热门技术文章，并深入爬取详情页获取完整内容
"""
import hashlib
import re
from datetime import datetime

from .base import BaseCrawler
from services.collection.detail_pipeline import DetailStrategyResult, limit_detail_content, run_detail_pipeline
from services.collection.html_article_extractor import HtmlArticleExtractor


class CnblogsCrawler(BaseCrawler):
    """
    博客园爬虫
    通过博客园API和网页端获取热门技术文章
    爬取频率：每2小时一次
    """

    SITE_HOME_URL = "https://www.cnblogs.com/sitehome/p/1"
    AGG_SITE_URL = "https://www.cnblogs.com/aggsite/top"
    PICK_URL = "https://www.cnblogs.com/pick/"

    def __init__(self):
        super().__init__("cnblogs", "博客园")

    def crawl(self) -> list:
        results = []
        for url in [self.AGG_SITE_URL, self.PICK_URL, self.SITE_HOME_URL]:
            try:
                results = self._crawl_web_page(url)
                if results:
                    return results
            except Exception:
                continue
        return results

    def _crawl_web_page(self, url: str) -> list:
        headers = self._build_headers()
        headers["Referer"] = "https://www.cnblogs.com/"
        response = self.fetch(url, headers=headers)
        html = response.text
        results = []
        post_pattern = re.findall(
            r'<a[^>]*class="post-item-title"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            html, re.DOTALL
        )
        if not post_pattern:
            post_pattern = re.findall(
                r'<a[^>]*href="(https://www\.cnblogs\.com/[^/]+/p/[^"]+)"[^>]*class="titlelnk"[^>]*>([^<]+)</a>',
                html, re.DOTALL
            )
        if not post_pattern:
            post_pattern = re.findall(
                r'<a[^>]*href="(https://www\.cnblogs\.com/[^/]+/p/[^"]+)"[^>]*>([^<]{6,}?)</a>',
                html, re.DOTALL
            )
        seen = set()
        for post_url, title in post_pattern[:20]:
            title = title.strip()
            if not title or post_url in seen:
                continue
            seen.add(post_url)
            post_id = hashlib.md5(post_url.encode()).hexdigest()[:16]
            source_id = hashlib.md5(f"cnblogs_{post_id}".encode()).hexdigest()[:16]
            results.append({
                "source_id": source_id,
                "title": title[:40],
                "content": title[:500],
                "source_url": post_url,
                "event_time": datetime.now(),
                "core_entity": title[:20],
                "location": "",
                "indicator_name": "",
                "indicator_value": "",
                "_allow_title_only": True,
            })
        return results

    def fetch_detail(self, source_url: str, item: dict) -> str:
        return self.resolve_detail(item).content

    def resolve_detail(self, item: dict):
        candidates = []
        html = self._fetch_detail_html(item)
        if html:
            post_body_content = self._extract_post_body(html)
            if post_body_content:
                candidates.append(
                    DetailStrategyResult(strategy="cnblogs_post_body", content=limit_detail_content(post_body_content))
                )

            article_text = HtmlArticleExtractor().extract(html)
            if len(article_text) >= 50:
                candidates.append(
                    DetailStrategyResult(strategy="html_article", content=limit_detail_content(article_text))
                )

        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )

    def _fetch_detail_html(self, item: dict) -> str:
        source_url = item.get("source_url", "")
        if not source_url:
            return ""
        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.cnblogs.com/"
            response = self.fetch(source_url, headers=headers, timeout=8)
            return response.text
        except Exception as e:
            self.logger.warning(f"博客园详情HTML获取失败: {e}")
            return ""

    def _fetch_post_body_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.cnblogs.com/"
            response = self.fetch(source_url, headers=headers)
            content = self._extract_post_body(response.text)
            if content:
                return DetailStrategyResult(strategy="cnblogs_post_body", content=limit_detail_content(content))
        except Exception as e:
            self.logger.warning(f"博客园详情爬取失败: {e}")
        return None

    def _fetch_html_article_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            headers = self._build_headers()
            headers["Referer"] = "https://www.cnblogs.com/"
            response = self.fetch(source_url, headers=headers)
            text = HtmlArticleExtractor().extract(response.text)
            if len(text) >= 50:
                return DetailStrategyResult(strategy="html_article", content=limit_detail_content(text))
        except Exception as e:
            self.logger.warning(f"博客园HTML正文兜底失败: {e}")
        return None

    def _extract_post_body(self, html: str) -> str:
        patterns = (
            r'<div[^>]*(?:id|class)=["\'](?:cnblogs_post_body|cnblogs-post-body|article_content)["\'][^>]*>(.*?)(?:<div[^>]+id=["\']blog-comments-placeholder|<div[^>]+id=["\']post_next_prev|</body>)',
            r'<article[^>]*(?:id|class)=["\'][^"\']*article_content[^"\']*["\'][^>]*>(.*?)</article>',
        )
        for pattern in patterns:
            match = re.search(pattern, html or "", re.DOTALL | re.IGNORECASE)
            if not match:
                continue
            content = match.group(1)
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<(?:nav|footer|header|aside)[^>]*>.*?</(?:nav|footer|header|aside)>", " ", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"</(?:p|h1|h2|h3|li|div|section)>", "。", content, flags=re.IGNORECASE)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = re.sub(r'。+', '。', content).strip(" 。\t\r\n")
            if len(content) >= 50:
                return content
        return ""

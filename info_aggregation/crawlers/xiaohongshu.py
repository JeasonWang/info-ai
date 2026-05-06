"""
信息聚合系统 - 小红书爬虫
爬取小红书热门笔记，使用桌面版探索页+详情页获取完整内容
"""
import hashlib
import re
import json
from http.cookies import SimpleCookie
from datetime import datetime

from .base import BaseCrawler
from services.credential_provider import get_credential
from services.detail_pipeline import DetailStrategyResult, limit_detail_content, run_detail_pipeline


class XiaohongshuCrawler(BaseCrawler):
    """
    小红书爬虫
    通过小红书桌面端获取热门笔记
    爬取频率：每30分钟一次
    """

    EXPLORE_URL = "https://www.xiaohongshu.com/explore"
    DETAIL_URL_TEMPLATE = "https://www.xiaohongshu.com/explore/{}"

    def __init__(self):
        super().__init__("xiaohongshu", "小红书")

    def _get_xhs_cookie(self) -> str:
        return get_credential("XHS_COOKIE")

    def _build_headers(self) -> dict:
        """构建桌面版请求头"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.xiaohongshu.com/",
            "Upgrade-Insecure-Requests": "1",
        }
        cookie = self._get_xhs_cookie()
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def _is_valid_content(self, text: str) -> bool:
        """检查内容是否有效，过滤掉错误页面和备案信息"""
        if not text or len(text.strip()) < 50:
            return False
        
        invalid_keywords = [
            "你访问的页面不见了",
            "请先登录",
            "登录后查看",
            "验证后继续访问",
            "滑块验证",
            "沪ICP备",
            "营业执照",
            "增值电信业务经营许可证",
            "互联网药品信息服务资格证书",
            "行吟信息科技",
        ]
        
        for keyword in invalid_keywords:
            if keyword in text:
                return False
        
        return True

    def _extract_initial_state(self, html: str) -> dict:
        """从HTML中提取__INITIAL_STATE__ JSON数据"""
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
        if match:
            json_str = match.group(1)
            json_str = re.sub(r':undefined', ':null', json_str)
            try:
                return json.loads(json_str)
            except Exception as e:
                self.logger.warning(f"JSON解析失败: {e}")
        return {}

    def crawl(self) -> list:
        """执行爬取"""
        results = []
        try:
            headers = self._build_headers()
            response = self.fetch(self.EXPLORE_URL, headers=headers)
            html = response.text
            
            self.logger.info(f"探索页HTML长度: {len(html)}")
            
            state = self._extract_initial_state(html)
            if not state:
                self.logger.warning("未找到INITIAL_STATE数据")
                return results
            
            results = self._parse_feed_data(state)
            
        except Exception as e:
            self.logger.error(f"小红书爬取异常: {e}", exc_info=True)
        
        return results[:20]

    def _parse_feed_data(self, state: dict) -> list:
        """解析探索页feed数据"""
        results = []
        
        feeds = state.get('feed', {}).get('feeds', [])
        self.logger.info(f"解析到feed数量: {len(feeds)}")
        
        for feed_item in feeds:
            try:
                note_info = self._extract_note_from_feed(feed_item)
                if note_info:
                    results.append(note_info)
            except Exception as e:
                self.logger.warning(f"解析feed项失败: {e}")
        
        return results

    def _extract_note_from_feed(self, feed_item: dict) -> dict:
        """从feed项中提取笔记信息"""
        note_id = feed_item.get('id', '')
        xsec_token = feed_item.get('xsecToken', '')
        note_card = feed_item.get('noteCard', {})
        
        if not note_id:
            return None
        
        title = note_card.get('displayTitle', '').strip()
        if not title:
            return None
        desc = (
            note_card.get("desc")
            or note_card.get("description")
            or note_card.get("displayContent")
            or ""
        )
        desc = str(desc).strip()
        content = self._combine_note_card_content(title=title, desc=desc, note_card=note_card)
        if self._is_low_information_note(title, content, note_card):
            return None
        
        source_id = hashlib.md5(f"xhs_{note_id}".encode()).hexdigest()[:16]
        
        source_url = f"{self.DETAIL_URL_TEMPLATE.format(note_id)}?xsec_token={xsec_token}" if xsec_token else self.DETAIL_URL_TEMPLATE.format(note_id)
        
        return {
            "source_id": source_id,
            "title": title[:40],
            "content": content[:500],
            "source_url": source_url,
            "event_time": datetime.now(),
            "core_entity": title[:20],
            "location": "",
            "indicator_name": "",
            "indicator_value": "",
            "_note_id": note_id,
            "_xsec_token": xsec_token,
            "_search_content": content if len(content) >= 30 else "",
            "_allow_title_only": True,
        }

    def _combine_note_card_content(self, title: str, desc: str, note_card: dict) -> str:
        parts = [part for part in [title, desc] if part]
        tag_names = self._extract_tag_names(note_card)
        if tag_names:
            parts.append("标签：" + "、".join(tag_names[:8]))
        interaction_text = self._extract_interaction_text(note_card.get("interactInfo", {}) or note_card.get("interact", {}) or {})
        if interaction_text:
            parts.append(interaction_text)
        return "。".join(parts)

    def _is_low_information_note(self, title: str, content: str, note_card: dict) -> bool:
        """过滤纯口号、纯图片或正文过短且无互动信号的笔记，减少低价值入口进入详情链。"""
        plain_text = re.sub(r"\s+", "", content or "")
        if len(plain_text) >= 18:
            return False
        interaction_text = self._extract_interaction_text(note_card.get("interactInfo", {}) or note_card.get("interact", {}) or {})
        tags = self._extract_tag_names(note_card)
        return not interaction_text and len(tags) == 0 and len((title or "").strip()) < 14

    def _extract_tag_names(self, note: dict) -> list[str]:
        tag_names = []
        for tag in note.get("tagList", []) or note.get("tags", []) or []:
            if isinstance(tag, dict):
                name = str(tag.get("name") or tag.get("tagName") or "").strip()
            else:
                name = str(tag or "").strip()
            if name:
                tag_names.append(name)
        return tag_names

    def _extract_interaction_text(self, interact_info: dict) -> str:
        interaction_parts = []
        for key, label in (
            ("likedCount", "点赞"),
            ("collectedCount", "收藏"),
            ("commentCount", "评论"),
            ("shareCount", "分享"),
        ):
            value = interact_info.get(key)
            if value not in (None, "", "0", 0):
                interaction_parts.append(f"{label}{value}")
        return "互动：" + "，".join(interaction_parts) if interaction_parts else ""

    def fetch_detail(self, source_url: str, item: dict) -> str:
        return self.resolve_detail(item).content

    def resolve_detail(self, item: dict):
        candidates = []
        html = self._fetch_detail_html(item)
        if html:
            initial_state_detail = self._extract_initial_state_detail_from_html(html)
            if initial_state_detail:
                candidates.append(initial_state_detail)
            html_text_detail = self._extract_html_text_detail_from_html(html)
            if html_text_detail:
                candidates.append(html_text_detail)

        initial_result = run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )
        if initial_result.status in {"complete", "partial"}:
            return initial_result

        rendered_detail = self._fetch_rendered_detail(item)
        if rendered_detail:
            candidates.append(rendered_detail)

        return run_detail_pipeline(
            title=item.get("title", ""),
            list_content=item.get("content", ""),
            strategy_results=candidates,
            channel_code=self.channel_code,
        )

    def _fetch_rendered_detail(self, item: dict):
        """使用浏览器渲染兜底动态笔记页，避免只拿到空壳 HTML。"""
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            self.logger.warning(f"Playwright 不可用，小红书渲染兜底跳过: {e}")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self._build_headers().get("User-Agent"),
                    locale="zh-CN",
                    viewport={"width": 1365, "height": 900},
                )
                self._apply_cookie_to_context(context)
                page = context.new_page()
                page.goto(source_url, wait_until="domcontentloaded", timeout=12000)
                page.wait_for_timeout(800)

                state = page.evaluate(
                    """() => {
                        try {
                            return JSON.parse(JSON.stringify(window.__INITIAL_STATE__ || null));
                        } catch (e) {
                            return null;
                        }
                    }"""
                )
                if state:
                    content = self._extract_content_from_state(state)
                    if content and self._is_valid_content(content):
                        browser.close()
                        return DetailStrategyResult(
                            strategy="rendered_initial_state",
                            content=limit_detail_content(content),
                        )

                text = page.evaluate(
                    """() => {
                        const meta = document.querySelector('meta[name="description"]')?.content || '';
                        const title = document.querySelector('h1')?.innerText || '';
                        const body = document.body?.innerText || '';
                        return [title, meta, body].filter(Boolean).join('\\n');
                    }"""
                )
                browser.close()
                cleaned = self._extract_rendered_note_text(text, item.get("title", ""))
                if cleaned and self._is_valid_content(cleaned):
                    return DetailStrategyResult(strategy="rendered_page", content=limit_detail_content(cleaned))
        except Exception as e:
            self.logger.warning(f"小红书渲染详情兜底失败: {e}")
        return None

    def _apply_cookie_to_context(self, context):
        cookie = self._get_xhs_cookie()
        if not cookie:
            return
        parsed = SimpleCookie()
        parsed.load(cookie)
        cookies = []
        for name, morsel in parsed.items():
            cookies.append({
                "name": name,
                "value": morsel.value,
                "domain": ".xiaohongshu.com",
                "path": "/",
            })
        if cookies:
            context.add_cookies(cookies)

    def _extract_rendered_note_text(self, text: str, title: str = "") -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        if not cleaned:
            return ""
        stop_markers = [
            "相关推荐",
            "展开更多",
            "登录",
            "版权所有",
            "沪ICP备",
        ]
        for marker in stop_markers:
            idx = cleaned.find(marker)
            if idx > 80:
                cleaned = cleaned[:idx].strip()
        if title and title in cleaned:
            idx = cleaned.find(title)
            cleaned = cleaned[idx:].strip()
        return cleaned

    def _fetch_detail_html(self, item: dict) -> str:
        source_url = item.get("source_url", "")
        if not source_url:
            return ""
        try:
            headers = self._build_headers()
            response = self.fetch(source_url, headers=headers, timeout=15)
            html = response.text
            if "你访问的页面不见了" in html:
                return ""
            return html
        except Exception as e:
            self.logger.warning(f"小红书详情HTML获取失败: {e}")
            return ""

    def _extract_initial_state_detail_from_html(self, html: str):
        state = self._extract_initial_state(html)
        if state:
            content = self._extract_content_from_state(state)
            if content and self._is_valid_content(content):
                return DetailStrategyResult(strategy="xhs_initial_state", content=limit_detail_content(content))
        return None

    def _extract_html_text_detail_from_html(self, html: str):
        text = self._extract_text_from_html(html)
        if text and self._is_valid_content(text):
            return DetailStrategyResult(strategy="html_text", content=limit_detail_content(text))
        return None

    def _fetch_initial_state_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            headers = self._build_headers()
            response = self.fetch(source_url, headers=headers, timeout=15)
            html = response.text
            if "你访问的页面不见了" in html:
                return None
            state = self._extract_initial_state(html)
            if state:
                content = self._extract_content_from_state(state)
                if content and self._is_valid_content(content):
                    return DetailStrategyResult(strategy="xhs_initial_state", content=limit_detail_content(content))
        except Exception as e:
            self.logger.warning(f"小红书INITIAL_STATE详情爬取失败: {e}")
        return None

    def _fetch_html_text_detail(self, item: dict):
        source_url = item.get("source_url", "")
        if not source_url:
            return None
        try:
            headers = self._build_headers()
            response = self.fetch(source_url, headers=headers, timeout=15)
            text = self._extract_text_from_html(response.text)
            if text and self._is_valid_content(text):
                return DetailStrategyResult(strategy="html_text", content=limit_detail_content(text))
        except Exception as e:
            self.logger.warning(f"小红书HTML详情兜底失败: {e}")
        return None

    def _legacy_fetch_detail(self, source_url: str, item: dict) -> str:
        """爬取详情页获取完整内容"""
        if not source_url:
            return ""
        
        try:
            headers = self._build_headers()
            response = self.fetch(source_url, headers=headers, timeout=15)
            html = response.text
            
            self.logger.info(f"详情页HTML长度: {len(html)}")
            
            if "你访问的页面不见了" in html:
                self.logger.warning("详情页返回'页面不见了'")
                return ""
            
            if "沪ICP备" in html and len(html) < 100000:
                self.logger.warning("详情页返回备案信息页面")
                return ""
            
            state = self._extract_initial_state(html)
            if state:
                content = self._extract_content_from_state(state)
                if content and self._is_valid_content(content):
                    return limit_detail_content(content)
            
            text = self._extract_text_from_html(html)
            if text and self._is_valid_content(text):
                return limit_detail_content(text)
            
            self.logger.warning("详情页未提取到有效内容")
            return ""
            
        except Exception as e:
            self.logger.warning(f"详情页爬取失败: {e}")
            return ""

    def _extract_content_from_state(self, state: dict) -> str:
        """从INITIAL_STATE中提取笔记内容"""
        note_data = state.get('note', {})
        detail_map = note_data.get('noteDetailMap', {})
        
        for note_id, note_info in detail_map.items():
            if note_id == 'undefined' or not isinstance(note_info, dict):
                continue
            
            note = note_info.get('note', {})
            if note:
                return self._combine_note_content(note)
        
        return ""

    def _combine_note_content(self, note: dict) -> str:
        """组合笔记标题和描述为完整内容"""
        title = note.get('title', '').strip()
        desc = note.get('desc', '').strip()
        
        content_parts = []
        if title:
            content_parts.append(title)
        if desc and desc != title:
            content_parts.append(desc)
        tag_names = self._extract_tag_names(note)
        if tag_names:
            content_parts.append("标签：" + "、".join(tag_names[:12]))

        interact_info = note.get("interactInfo", {}) or {}
        interaction_text = self._extract_interaction_text(interact_info)
        if interaction_text:
            content_parts.append(interaction_text)
        
        return "。".join(content_parts) if content_parts else ""

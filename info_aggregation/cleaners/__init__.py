"""
信息聚合系统 - 数据清洗模块
负责数据去重、格式规范化、字段截断等
"""
import re
import logging
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from config import CRAWLER_MAX_CONTENT_LENGTH
from services.data_quality import content_fingerprint, is_low_quality_list_item

logger = logging.getLogger(__name__)


def clean_title(title: str) -> str:
    """
    清洗标题：去除首尾空白、HTML标签，截断至40字
    参数:
        title: 原始标题
    返回:
        清洗后的标题
    """
    if not title:
        return ""
    title = re.sub(r"<[^>]+>", "", title)
    title = title.strip()
    title = re.sub(r"\s+", " ", title)
    return title[:40]


def clean_content(content: str) -> str:
    """
    清洗内容：去除HTML标签、多余空白，仅限制异常超长内容
    参数:
        content: 原始内容
    返回:
        清洗后的内容
    """
    if not content:
        return ""
    content = re.sub(r"<[^>]+>", "", content)
    content = content.strip()
    content = re.sub(r"\s+", " ", content)
    return content[:CRAWLER_MAX_CONTENT_LENGTH]


def clean_source_url(url: str) -> str:
    """
    清洗URL：确保URL格式合法
    参数:
        url: 原始URL
    返回:
        清洗后的URL
    """
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return ""
    if len(url) > 500:
        parsed = urlsplit(url)
        url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    if len(url) > 500:
        url = url[:500]
    return url


def clean_info_item(item: dict) -> dict:
    """
    清洗单条信息：对所有字段进行规范化处理
    参数:
        item: 原始信息字典
    返回:
        清洗后的信息字典，不合格返回None
    """
    if not item:
        return None

    title = clean_title(item.get("title", ""))
    if not title:
        return None

    content = clean_content(item.get("content", ""))
    allow_title_only = bool(item.get("_allow_title_only"))
    if is_low_quality_list_item(title, content) and not allow_title_only:
        return None

    source_url = clean_source_url(item.get("source_url", ""))
    source_id = item.get("source_id", "").strip()
    if not source_id:
        return None

    event_time = item.get("event_time")
    if not event_time:
        event_time = datetime.now()
    elif isinstance(event_time, str):
        try:
            event_time = datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            event_time = datetime.now()

    result = {
        "source_id": source_id,
        "title": title,
        "content": content,
        "source_url": source_url,
        "event_time": event_time,
        "core_entity": item.get("core_entity", "")[:100],
        "location": item.get("location", "")[:100],
        "indicator_name": item.get("indicator_name", "")[:100],
        "indicator_value": item.get("indicator_value", "")[:100],
    }
    for key, value in item.items():
        if key.startswith("_") and key not in result:
            result[key] = value
    return result


def clean_info_list(items: list) -> list:
    """
    批量清洗信息列表：过滤不合格数据，去重（按source_id和内容弱指纹）
    参数:
        items: 原始信息列表
    返回:
        清洗去重后的信息列表
    """
    cleaned = []
    seen_ids = set()
    seen_fingerprints = set()

    for item in items:
        result = clean_info_item(item)
        if result is None:
            continue
        if result["source_id"] in seen_ids:
            continue
        fingerprint = content_fingerprint(result["title"], result["content"])
        if fingerprint in seen_fingerprints:
            continue
        seen_ids.add(result["source_id"])
        seen_fingerprints.add(fingerprint)
        cleaned.append(result)

    logger.info(f"数据清洗: 输入{len(items)}条, 输出{len(cleaned)}条")
    return cleaned

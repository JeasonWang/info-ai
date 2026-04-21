"""
数据质量闸门。

这一层用于采集入库前的轻量质量判断，避免重复标题、标题即正文、
短列表摘要这类低价值内容持续进入数据库和事件流。
"""
from difflib import SequenceMatcher
import re


def normalize_text(value: str) -> str:
    """统一文本形态，方便做稳定的重复判断。"""
    text = re.sub(r"<[^>]+>", "", value or "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def text_similarity(left: str, right: str) -> float:
    """计算两段短文本的相似度。"""
    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)
    if not normalized_left or not normalized_right:
        return 0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def content_fingerprint(title: str, content: str) -> str:
    """生成弱指纹，用于批内去重。"""
    normalized_title = normalize_text(title)
    normalized_content = normalize_text(content)
    return f"{normalized_title}|{normalized_content[:120]}"


def is_title_content_duplicate(title: str, content: str) -> bool:
    """判断正文是否只是标题的重复或轻微扩写。"""
    normalized_title = normalize_text(title)
    normalized_content = normalize_text(content)
    if not normalized_title or not normalized_content:
        return False
    return text_similarity(normalized_title, normalized_content) >= 0.94 and len(normalized_content) <= len(normalized_title) + 8


def is_low_quality_list_item(title: str, content: str) -> bool:
    """过滤明显不适合入库的列表摘要。"""
    normalized_content = normalize_text(content)
    if not normalized_content:
        return True
    if len(normalized_content) < 12:
        return True
    return is_title_content_duplicate(title, content)


def is_near_duplicate_item(
    title: str,
    content: str,
    existing_title: str,
    existing_content: str,
    title_threshold: float = 0.94,
    content_threshold: float = 0.9,
) -> bool:
    """判断两条内容是否近似重复。"""
    return (
        text_similarity(title, existing_title) >= title_threshold
        and text_similarity(content, existing_content) >= content_threshold
    )

from difflib import SequenceMatcher
import re


PAGE_METADATA_PATTERNS = [
    r"[\w\-\u4e00-\u9fa5]{1,24}\s+20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s+\d+\s+阅读\d+分钟[。.\s]*",
    r"20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s+\d+\s+阅读\d+分钟[。.\s]*",
    r"\d+\s*阅读\d+分钟[。.\s]*",
    r"阅读\d+分钟[。.\s]*",
    r"\d+\s*浏览[。.\s]*",
    r"\d+\s*评论[。.\s]*",
]


def normalize_inline_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def clean_source_text(text: str) -> str:
    cleaned = text or ""
    for pattern in PAGE_METADATA_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"复制代码|展开阅读全文|收起全文|打开APP查看全部内容", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ，。:：;；")


def split_sentences(text: str) -> list[str]:
    cleaned = clean_source_text(text)
    if not cleaned:
        return []
    chunks = re.split(r"(?<=[。！？!?])\s+|(?<=[。！？!?])", cleaned)
    sentences: list[str] = []
    for chunk in chunks:
        sentence = chunk.strip(" ，,;；:：")
        if len(sentence) < 8:
            continue
        sentences.append(ensure_sentence_end(sentence))
    return sentences


def ensure_sentence_end(text: str) -> str:
    value = normalize_inline_text(text).rstrip("，,;；:：、")
    if not value:
        return ""
    if value.endswith(("。", "！", "？", ".", "!", "?")):
        return value
    return f"{value}。"


def natural_clip(text: str, max_length: int, min_length: int = 28) -> str:
    value = clean_source_text(text)
    if len(value) <= max_length:
        return ensure_sentence_end(value)
    sentences = split_sentences(value)
    selected: list[str] = []
    total = 0
    for sentence in sentences:
        if total + len(sentence) > max_length and total >= min_length:
            break
        selected.append(sentence)
        total += len(sentence)
    if selected:
        return ensure_sentence_end("".join(selected))
    return ensure_sentence_end(value[:max_length].rstrip("，,;；:：、"))


def text_similarity(left: str, right: str) -> float:
    left_norm = normalize_inline_text(left)
    right_norm = normalize_inline_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def remove_title_prefix(text: str, title: str) -> str:
    value = clean_source_text(text)
    title_value = normalize_inline_text(title)
    if title_value and value.startswith(title_value):
        value = value[len(title_value) :].lstrip(" ，。:：;；")
    return value

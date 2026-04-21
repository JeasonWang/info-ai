"""
科技内容轻量结构化解析器。

这一层先做规则驱动的轻量识别，目标不是完全 NLP 化，
而是为 Plus 阶段提供稳定、可解释的科技主题与关键词抽取结果。
"""
from dataclasses import dataclass, field
import re


TECH_TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("chip_release", ("芯片", "GPU", "显卡", "显存", "算力", "CUDA", "H100", "H200", "Blackwell")),
    ("dev_tool", ("编程", "开发者", "IDE", "API", "框架", "SDK", "开源", "MCP")),
    ("model_release", ("模型", "大模型", "推理", "训练", "token", "上下文", "Agent", "智能体")),
]

ENTITY_MARKERS = (
    "OpenAI",
    "Anthropic",
    "Google",
    "Meta",
    "微软",
    "英伟达",
    "AMD",
    "苹果",
    "阿里云",
    "字节跳动",
    "DeepSeek",
    "Claude",
    "Cursor",
    "MCP",
    "CUDA",
    "H100",
    "H200",
)

KEYWORD_MARKERS = (
    "显存",
    "训练效率",
    "部署成本",
    "推理",
    "训练",
    "token",
    "上下文",
    "上下文长度",
    "开发工具",
    "开发者工作流",
    "API",
    "算力",
    "多模态",
    "Agent",
    "智能体",
    "编程效率",
)


@dataclass
class TechContentParseResult:
    """科技内容结构化结果。"""

    topic_type: str = ""
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


def _add_unique(items: list[str], seen: set[str], value: str):
    cleaned = value.strip()
    if not cleaned or cleaned in seen:
        return
    items.append(cleaned)
    seen.add(cleaned)


def _extract_entities(text: str) -> list[str]:
    entities: list[str] = []
    seen: set[str] = set()

    for marker in ENTITY_MARKERS:
        if marker in text:
            _add_unique(entities, seen, marker)

    # 补充抽取常见型号/缩写，保证 H200、RTX5090 这类对象能被保留下来。
    for token in re.findall(r"\b[A-Za-z]{1,6}\d{2,5}\b", text):
        _add_unique(entities, seen, token)

    return entities


def _extract_keywords(text: str) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()

    for marker in KEYWORD_MARKERS:
        if marker in text:
            _add_unique(keywords, seen, marker)

    # 补充提取常见双词科技短语，优先保留更有解释性的字段。
    for phrase in ("训练效率", "部署成本", "开发工具", "上下文长度", "开发者工作流"):
        if phrase in text:
            _add_unique(keywords, seen, phrase)

    return keywords


def _detect_topic_type(text: str) -> str:
    for topic_type, markers in TECH_TOPIC_RULES:
        if any(marker in text for marker in markers):
            return topic_type
    return ""


def parse_tech_content(title: str, content: str) -> TechContentParseResult:
    """
    解析科技内容，输出主题类型、实体和关键词。

    这一步只做轻量规则识别，后面如果要升级到模型或更复杂的词典，
    可以在保持接口不变的前提下继续增强。
    """
    text = f"{title or ''} {content or ''}".strip()
    if not text:
        return TechContentParseResult()

    return TechContentParseResult(
        topic_type=_detect_topic_type(text),
        entities=_extract_entities(text),
        keywords=_extract_keywords(text),
    )

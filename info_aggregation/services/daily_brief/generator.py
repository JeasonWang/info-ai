"""Generate daily brief content using LLM."""
import json
import logging
import time

from services.llm import (
    LLMChatMessage,
    LLMChatRequest,
    run_llm_chat_completion,
)
from services.analysis.llm_model_config import select_available_llm_config_independent
from .selector import get_event_summaries_for_brief

logger = logging.getLogger(__name__)

BRIEF_SYSTEM_PROMPT = """你是一个信息情报台的资深编辑，擅长撰写每日情报简报。你的读者是对时事敏感、需要快速了解当日重要事件脉络的专业人士。写作要求：
1. 标题要精炼有力，概括当日最重要的趋势或事件
2. 每个事件的描述要包含：一句话判断、核心事实、为什么值得关注
3. 语言客观、信息密度高，避免情绪化表达
4. 每个事件控制在3-5句话以内"""

BRIEF_USER_PROMPT_TEMPLATE = """请根据以下{event_count}个重要事件的信息，生成今日情报简报。

{events_text}

请按以下JSON格式输出：
{{
  "headline": "简报标题",
  "brief_text": "简报正文（Markdown格式，包含各事件的标题、判断和详情）",
  "events": [
    {{
      "title": "事件标题",
      "judgment": "一句话判断",
      "detail": "详细描述（2-3句话）"
    }}
  ]
}}"""


def _generate_fallback_brief(events: list[dict]) -> dict:
    """Generate a template-based brief when LLM is unavailable."""
    event_parts = []
    for idx, ev in enumerate(events, 1):
        event_parts.append(
            f"### {idx}. {ev['title']}" + chr(10) + chr(10)
            + f"{ev['one_line_summary']}" + chr(10) + chr(10)
        )
    headline = f"今日情报简报 | {len(events)}条重要事件"
    brief_text = "# " + headline + chr(10) + chr(10) + "".join(event_parts)
    parsed_events = [
        {
            "title": ev["title"],
            "judgment": ev["one_line_summary"],
            "detail": ev["one_line_summary"],
        }
        for ev in events
    ]
    return {
        "headline": headline,
        "brief_text": brief_text,
        "events": parsed_events,
        "model_name": "fallback",
        "llm_config_id": None,
    }


def generate_brief_content(events: list[dict], model_name: str = None) -> dict:
    """
    Generate daily brief using LLM.

    Returns: {headline, brief_text, events: [{title, judgment, detail}], model_name, llm_config_id}
    Falls back to a template-based brief if LLM fails.
    """
    if not events:
        logger.info("没有事件可供生成简报")
        return {
            "headline": "今日情报简报 | 暂无重大事件",
            "brief_text": "# 今日情报简报" + chr(10) + chr(10) + "暂无重大事件。",
            "events": [],
            "model_name": "fallback",
            "llm_config_id": None,
        }

    config = select_available_llm_config_independent()
    if config is None:
        logger.warning("没有可用的LLM模型配置，使用回退模板生成简报")
        return _generate_fallback_brief(events)

    events_text = get_event_summaries_for_brief(events)
    user_prompt = BRIEF_USER_PROMPT_TEMPLATE.format(
        event_count=len(events),
        events_text=events_text,
    )

    request = LLMChatRequest(
        messages=[
            LLMChatMessage(role="system", content=BRIEF_SYSTEM_PROMPT),
            LLMChatMessage(role="user", content=user_prompt),
        ],
        temperature=0.3,
        timeout_seconds=120,
        input_item_count=len(events),
        log_context={"source": "daily_brief"},
    )

    try:
        started = time.perf_counter()
        result = run_llm_chat_completion(config, request)
        logger.info(
            "LLM简报生成成功, model=%s, latency=%dms",
            result.model_name,
            result.latency_ms,
        )

        content = result.content.strip()
        # Strip markdown code fences if present
        if content.startswith(chr(96)*3):
            lines = content.split(chr(10))
            lines = [l for l in lines if not l.strip().startswith(chr(96)*3)]
            content = chr(10).join(lines).strip()

        parsed = json.loads(content)
        return {
            "headline": parsed.get("headline", ""),
            "brief_text": parsed.get("brief_text", ""),
            "events": parsed.get("events", []),
            "model_name": result.model_name,
            "llm_config_id": result.config_id,
        }
    except Exception as exc:
        logger.warning("LLM简报生成失败，使用回退模板: %s", exc)
        return _generate_fallback_brief(events)
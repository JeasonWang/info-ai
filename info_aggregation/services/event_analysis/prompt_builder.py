from dataclasses import dataclass

from config import EVENT_ANALYSIS_MAX_INPUT_CHARS

from .text_utils import natural_clip


@dataclass(frozen=True)
class EventAnalysisPrompt:
    system_prompt: str
    user_prompt: str
    source_item_ids: list[int]
    source_count: int
    prompt_version: str = "event_analysis_v2"


class EventAnalysisPromptBuilder:
    """Build task prompts for LLM event analysis without coupling to a provider."""

    system_prompt = "你是信息达人事件分析引擎，只输出严格JSON。"

    def build(self, items, chronological_items=None, history_context: str | None = None) -> EventAnalysisPrompt:
        chronological_items = chronological_items or items
        source_blocks = self._source_blocks(items)
        output_contract = (
            "请基于真实来源生成事件分析，不要简单截取原文，不要编造没有证据的事实。\n"
            "优先完成四类任务：1. 一句话总结；2. 事实经过；3. 影响与价值；4. 最新进展与风险。\n"
            "如果来源不足，请明确写出不确定性，不要把社交热度当作事实。\n"
            "一句话总结必须是35-90个中文字符的完整判断句，不能照抄标题，不能以逗号、顿号、连接词或未完成短语结尾。\n"
            "事实经过、最新进展、风险提示必须能被来源支撑；缺证据时写明“仍需核实”或“暂无可靠来源”。\n"
            "输出JSON字段：one_line_summary, what_happened, why_it_matters, latest_update, "
            "heat_reason, risk_notice, source_compare, analysis_confidence, evolution_summary, history_context。\n"
            "每个字段必须是通顺中文完整句子，不要输出Markdown，不要输出JSON之外的解释文字。\n\n"
        )
        user_prompt = output_contract
        if history_context:
            user_prompt += f"【历史背景】\n{history_context}\n\n"
        user_prompt += "【当前来源】\n" + "\n".join(source_blocks)
        return EventAnalysisPrompt(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            source_item_ids=[item.id for item in items if getattr(item, "id", None)],
            source_count=len(chronological_items),
        )

    def _source_blocks(self, items) -> list[str]:
        source_blocks: list[str] = []
        consumed = 0
        for index, item in enumerate(items[:8], start=1):
            content = natural_clip(item.content or "", 1800)
            block = (
                f"来源{index}\n"
                f"标题：{item.title}\n"
                f"渠道：{item.channel.name if getattr(item, 'channel', None) else item.channel_id}\n"
                f"时间：{item.event_time or item.created_at}\n"
                f"正文：{content}\n"
            )
            if consumed + len(block) > EVENT_ANALYSIS_MAX_INPUT_CHARS:
                break
            source_blocks.append(block)
            consumed += len(block)
        return source_blocks

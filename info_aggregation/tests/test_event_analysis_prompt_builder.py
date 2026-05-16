from datetime import datetime

from database import Category, Channel, Info
from services.event_analysis.prompt_builder import EventAnalysisPromptBuilder
from services.event_analysis.providers import OpenAICompatibleEventAnalysisProvider
from services.event_analysis.result_parser import EventAnalysisResultParser
from services.event_analysis.tasks import default_event_analysis_tasks
from services.llm.chat import LLMChatResult


def _info(session):
    category = Category(name="科技", code="tech")
    channel = Channel(name="掘金", code="juejin", category_rel=category)
    session.add_all([category, channel])
    session.flush()
    item = Info(
        title="OpenAI 发布新模型能力",
        content="OpenAI 发布新模型能力，开发者关注 API 接入、推理成本和企业部署路径。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="prompt-builder",
        source_url="https://example.com/prompt-builder",
        event_time=datetime(2026, 5, 13, 9, 0, 0),
    )
    session.add(item)
    session.commit()
    return item


def test_event_analysis_prompt_builder_separates_task_prompt_and_log_context(session):
    item = _info(session)

    prompt = EventAnalysisPromptBuilder().build([item], [item], history_context="上一轮模型发布带来价格变化。")

    assert prompt.prompt_version == "event_analysis_v2"
    assert prompt.source_item_ids == [item.id]
    assert "只输出严格JSON" in prompt.system_prompt
    assert "不要把社交热度当作事实" in prompt.user_prompt
    assert "35-90个中文字符" in prompt.user_prompt
    assert "不能照抄标题" in prompt.user_prompt
    assert "上一轮模型发布带来价格变化" in prompt.user_prompt
    assert "OpenAI 发布新模型能力" in prompt.user_prompt


def test_event_analysis_prompt_builder_includes_structured_llm_tasks(session):
    item = _info(session)
    tasks = default_event_analysis_tasks()

    prompt = EventAnalysisPromptBuilder().build([item], [item], tasks=tasks)

    assert prompt.task_codes == ["summary", "fact_check", "source_compare", "history_relation"]
    assert "【分析任务】" in prompt.user_prompt
    assert "事实校验" in prompt.user_prompt
    assert "多源叙事差异" in prompt.user_prompt
    assert "历史关联判断" in prompt.user_prompt
    assert "fact_check -> risk_notice" in prompt.user_prompt


def test_openai_compatible_provider_logs_event_analysis_task_codes(session, monkeypatch):
    item = _info(session)

    class FakeChatClient:
        def __init__(self, config):
            self.config = config

        def chat(self, request):
            return LLMChatResult(
                config_id=self.config.id,
                provider_code=self.config.provider_code,
                model_name=self.config.model_name,
                content=(
                    '{"one_line_summary":"OpenAI 新模型引发开发者持续关注。",'
                    '"what_happened":"OpenAI 发布新模型能力。",'
                    '"why_it_matters":"开发者关注 API 接入和企业部署路径。",'
                    '"latest_update":"当前讨论集中在推理成本和部署方式。",'
                    '"heat_reason":"多个技术社区持续讨论。",'
                    '"risk_notice":"仍需核实价格和企业部署细节。",'
                    '"source_compare":"当前主要来自技术社区来源。",'
                    '"analysis_confidence":"分析可信度：中。"}'
                ),
                latency_ms=12,
                status_code=200,
                usage={},
                raw_response={"choices": [{"message": {"content": "ok"}}]},
            )

    monkeypatch.setattr("services.event_analysis.providers.OpenAICompatibleChatClient", FakeChatClient)

    provider = OpenAICompatibleEventAnalysisProvider(base_url="http://127.0.0.1:8001/v1", api_key="sk-test")
    provider.analyze([item], [item], tasks=default_event_analysis_tasks())

    assert provider.last_request_payload["context"]["task_codes"] == [
        "summary",
        "fact_check",
        "source_compare",
        "history_relation",
    ]
    assert "事实校验" in provider.last_request_payload["messages"][1]["content"]


def test_event_analysis_result_parser_preserves_provider_and_used_sources(session):
    item = _info(session)
    data = {
        "one_line_summary": "OpenAI 新模型引发开发者关注。",
        "what_happened": "OpenAI 发布新模型能力。",
        "why_it_matters": "开发者关注接入成本。",
        "latest_update": "当前讨论集中在 API。",
        "heat_reason": "多个技术社区关注。",
        "risk_notice": "仍需观察价格细节。",
        "source_compare": "当前主要来自技术社区。",
        "analysis_confidence": "分析可信度：中。",
    }

    result = EventAnalysisResultParser().parse(data, [item], provider="qwen", model_name="qwen-max")

    assert result.provider == "qwen"
    assert result.model_name == "qwen-max"
    assert result.used_info_ids == [item.id]
    assert result.timeline_points[0].source_item_id == item.id

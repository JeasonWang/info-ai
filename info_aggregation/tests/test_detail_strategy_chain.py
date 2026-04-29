from services.detail_pipeline import DetailStrategyResult
from services.detail_strategy_chain import DetailContext, DetailStrategyChain


class StaticStrategy:
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content
        self.calls = 0

    def fetch(self, context: DetailContext) -> DetailStrategyResult:
        self.calls += 1
        return DetailStrategyResult(strategy=self.name, content=self.content)


def test_detail_strategy_chain_stops_after_complete_result():
    first = StaticStrategy(
        "api",
        "OpenAI 发布新模型，开发者关注推理能力、API 接入节奏、部署成本和企业应用落地节奏。",
    )
    second = StaticStrategy("rendered", "不应执行")
    chain = DetailStrategyChain([first, second])

    result = chain.run(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://example.com/a",
            channel_code="36kr",
        )
    )

    assert result.status == "complete"
    assert result.strategy == "api"
    assert second.calls == 0


def test_detail_strategy_chain_keeps_best_partial_before_fallback():
    weak = StaticStrategy("weak_html", "一段与标题主体不匹配但长度足够的正文内容，用于模拟弱相关页面。")
    short = StaticStrategy("short_api", "OpenAI 发布")
    chain = DetailStrategyChain([weak, short])

    result = chain.run(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://example.com/b",
            channel_code="36kr",
        )
    )

    assert result.status == "partial"
    assert result.strategy == "weak_html"
    assert result.failure_reason == "weak_relevance"

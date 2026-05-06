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
    complete_content = (
        "OpenAI 发布新模型，公司表示产品已经进入企业客户试用阶段，市场关注推理能力、API 接入节奏、"
        "部署成本和企业应用落地节奏。第一批开发者认为，这次更新会影响智能体工作流、企业知识库、"
        "自动化客服和数据分析场景。多家公司开始评估调用价格、稳定性、模型治理和私有化部署方案。"
        "行业分析人士认为，AI 基础设施、算力采购、云服务和应用生态都会受到影响。"
        "这篇商业分析继续补充融资、产品、市场和商业落地信息，说明相关公司正在围绕 AI 产品能力、"
        "客户增长、生态合作和收入模式展开竞争。企业用户也会关注安全审计、权限控制、区域合规和"
        "长期服务稳定性，开发者则更关心 SDK、文档、错误处理、吞吐量和上下文窗口。"
        "随着更多企业测试上线，市场会持续观察公司收入、客户留存、产品口碑和行业竞争格局。"
        "报道还提到，公司会继续扩大生态合作，推动更多软件厂商接入新模型能力，并用案例证明"
        "产品在客服、办公、研发和数据处理中的商业价值。投资者关注该产品能否带来持续收入，"
        "客户则关注部署周期、服务等级协议、数据隔离和合规审计。"
        "如果后续产品表现稳定，更多行业客户可能把 AI 能力嵌入核心流程，带动商业软件、云服务、"
        "咨询实施和数据治理市场继续增长。"
    )
    first = StaticStrategy(
        "api",
        complete_content,
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


def test_detail_strategy_chain_uses_channel_specific_thresholds():
    first = StaticStrategy(
        "api",
        "OpenAI 发布新模型，开发者关注推理能力、API 接入节奏、部署成本和企业应用落地节奏。",
    )
    chain = DetailStrategyChain([first])

    result = chain.run(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://example.com/a",
            channel_code="36kr",
        )
    )

    assert result.status == "partial"
    assert result.failure_reason == "content_below_channel_complete_threshold"
    assert chain.execution_logs[0]["strategy"] == "api"
    assert chain.execution_logs[0]["elapsed_ms"] >= 0


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

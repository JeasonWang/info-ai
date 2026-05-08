from services.detail_strategy_chain import DetailContext, DetailStrategyChain
from services.secondary_search_detail_strategy import (
    SecondarySearchDetailStrategy,
    WeiboSecondarySearchDetailStrategy,
    XiaohongshuSecondarySearchDetailStrategy,
    ZhihuSecondarySearchDetailStrategy,
)


COMPLETE_ARTICLE_HTML = """
<article>
  <p>OpenAI 发布新模型，开发者关注推理能力、API 接入节奏、企业部署成本和落地周期。</p>
  <p>公司表示，新模型将面向企业客户开放试用，重点覆盖知识管理、自动化办公、客服和研发辅助。</p>
  <p>行业人士认为，企业会继续关注调用价格、服务稳定性、权限隔离、数据安全和区域合规要求。</p>
  <p>云服务厂商也会围绕算力、存储、网络、安全审计和监控能力提供配套服务，帮助客户降低上线风险。</p>
  <p>投资者则会观察客户增长、续费率、毛利率和生态合作进展，判断产品能否形成长期商业壁垒。</p>
  <p>从市场角度看，AI 产品竞争正在从单点模型能力转向完整解决方案，企业更关注稳定交付和真实收益。</p>
  <p>这也会推动更多公司重新评估预算、组织流程和数据资产治理，把 AI 能力嵌入核心业务流程。</p>
  <p>多位产业人士表示，企业采购新模型时不会只比较单次调用能力，还会综合评估工程接入、私有数据治理、审计追踪、成本预测和长期服务支持。</p>
  <p>对于软件公司来说，谁能把模型能力稳定嵌入销售、财务、人力、研发和客户服务等高频场景，谁就更容易形成可持续的产品价值。</p>
  <p>因此，这次发布不仅是一次技术更新，也会影响企业软件、云基础设施、咨询服务和行业应用公司的竞争节奏。</p>
  <p>后续市场还会关注生态伙伴数量、标杆客户案例、真实业务降本效果以及模型在复杂任务中的稳定表现。</p>
</article>
"""


def test_secondary_search_detail_strategy_fetches_candidate_article():
    seen_search_urls = []
    seen_article_urls = []

    def search_fetcher(url: str) -> str:
        seen_search_urls.append(url)
        return """
        <a href="https://www.36kr.com/p/original">原热词页</a>
        <a href="https://www.36kr.com/p/real-article">真实文章</a>
        <a href="https://example.com/noise">噪声</a>
        """

    def article_fetcher(url: str) -> str:
        seen_article_urls.append(url)
        return COMPLETE_ARTICLE_HTML

    strategy = SecondarySearchDetailStrategy(search_fetcher=search_fetcher, article_fetcher=article_fetcher)
    result = strategy.fetch(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://www.36kr.com/p/original",
            channel_code="36kr",
            strategy_hint="search_secondary_detail_source",
        )
    )

    assert "site%3A36kr.com" in seen_search_urls[0]
    assert seen_article_urls == ["https://www.36kr.com/p/real-article"]
    assert result.strategy == "secondary_search"
    assert "企业客户" in result.content
    assert result.matched_rules == ["secondary_search_url:https://www.36kr.com/p/real-article"]


def test_secondary_search_detail_strategy_can_complete_in_chain():
    strategy = SecondarySearchDetailStrategy(
        search_fetcher=lambda url: '<a href="https://www.36kr.com/p/real-article">真实文章</a>',
        article_fetcher=lambda url: COMPLETE_ARTICLE_HTML,
    )
    chain = DetailStrategyChain([strategy])

    result = chain.run(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://www.36kr.com/p/original",
            channel_code="36kr",
            strategy_hint="search_secondary_detail_source",
        )
    )

    assert result.status == "complete"
    assert result.strategy == "secondary_search"
    assert "secondary_search_url:https://www.36kr.com/p/real-article" in result.matched_rules


def test_channel_specific_secondary_search_strategies_use_specific_queries():
    strategies = [
        (ZhihuSecondarySearchDetailStrategy(), "site%3Azhihu.com%2Fquestion"),
        (XiaohongshuSecondarySearchDetailStrategy(), "site%3Axiaohongshu.com%2Fexplore"),
        (WeiboSecondarySearchDetailStrategy(), "site%3Aweibo.com"),
    ]

    for strategy, expected_query_part in strategies:
        assert expected_query_part in strategy._build_search_url("OpenAI 发布新模型", "")

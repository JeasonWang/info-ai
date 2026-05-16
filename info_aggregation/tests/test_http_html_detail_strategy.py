from services.collection.detail_strategy_chain import DetailContext, DetailStrategyChain
from services.collection.http_html_detail_strategy import HttpHtmlDetailStrategy, TrafilaturaArticleExtractor


def test_trafilatura_extractor_is_preferred_and_falls_back_to_html_extractor():
    extractor = TrafilaturaArticleExtractor(extract_func=lambda html: "Trafilatura 抽取出的高质量正文，包含更多有效段落和上下文信息。")

    assert "高质量正文" in extractor.extract("<html><body>噪声</body></html>")

    fallback = TrafilaturaArticleExtractor(extract_func=lambda html: "")
    content = fallback.extract("<article><p>OpenAI 发布新模型，企业客户关注 API 成本和部署节奏。</p></article>")

    assert "企业客户" in content


def test_http_html_detail_strategy_fetches_and_extracts_article():
    seen_urls = []

    def fetcher(url: str) -> str:
        seen_urls.append(url)
        return """
        <html><body>
          <article>
            <h1>OpenAI 发布新模型</h1>
            <p>OpenAI 发布新模型，开发者关注推理能力、API 接入节奏和部署成本。</p>
            <p>企业客户正在评估稳定性、数据安全边界和落地节奏。</p>
          </article>
        </body></html>
        """

    strategy = HttpHtmlDetailStrategy(fetcher=fetcher)
    result = strategy.fetch(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://example.com/openai",
            channel_code="36kr",
        )
    )

    assert seen_urls == ["https://example.com/openai"]
    assert result.strategy == "http_html_article"
    assert "企业客户" in result.content


def test_http_html_detail_strategy_returns_empty_content_when_url_missing():
    strategy = HttpHtmlDetailStrategy(fetcher=lambda url: "不应调用")

    result = strategy.fetch(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="",
            channel_code="36kr",
        )
    )

    assert result.content == ""
    assert result.failure_reason == "missing_source_url"


def test_http_html_detail_strategy_can_complete_in_strategy_chain():
    strategy = HttpHtmlDetailStrategy(
        fetcher=lambda url: """
        <article>
          <p>OpenAI 发布新模型，开发者关注推理能力、API 接入节奏、部署成本和企业落地节奏。</p>
          <p>公司表示，新模型会进入企业客户试用阶段，并围绕产品能力、商业落地、市场增长和生态合作继续扩展。</p>
          <p>多家企业正在评估调用价格、稳定性、模型治理、数据隔离、权限控制和区域合规方案。</p>
          <p>行业分析人士认为，这会影响 AI 基础设施、云服务采购、软件集成和自动化办公产品的商业竞争。</p>
          <p>开发者关注 SDK、文档、错误处理、上下文窗口、吞吐量和监控能力，企业则关注服务等级协议和长期稳定性。</p>
          <p>如果后续产品表现稳定，更多行业客户可能把 AI 能力嵌入核心流程，带动咨询实施、数据治理和应用生态增长。</p>
          <p>报道进一步分析，商业软件厂商会把新模型能力包装进办公、客服、研发、数据分析和知识管理产品。</p>
          <p>云服务厂商也会围绕算力、存储、网络、安全审计和模型监控提供配套能力，帮助企业降低上线风险。</p>
          <p>投资者则会观察客户增长、续费率、毛利率和生态合作进展，判断这项产品是否能够形成长期商业壁垒。</p>
          <p>从市场角度看，AI 产品竞争已经从单点模型能力转向完整解决方案，企业会更关注稳定交付和真实业务收益。</p>
          <p>这也会推动更多公司重新评估预算、组织流程和数据资产治理。</p>
        </article>
        """
    )
    chain = DetailStrategyChain([strategy])

    result = chain.run(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://example.com/openai",
            channel_code="36kr",
        )
    )

    assert result.status == "complete"
    assert result.strategy == "http_html_article"

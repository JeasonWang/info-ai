from services.detail_strategy_chain import DetailContext, DetailStrategyChain
from services.http_html_detail_strategy import HttpHtmlDetailStrategy, TrafilaturaArticleExtractor


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

from services.collection.detail_strategy_chain import DetailContext
from services.collection.html_article_extractor import HtmlArticleExtractor, StaticHtmlArticleStrategy


def test_html_article_extractor_prefers_article_text():
    html = """
    <html>
      <body>
        <nav>首页 登录 注册</nav>
        <article>
          <h1>OpenAI 发布新模型</h1>
          <p>OpenAI 发布新模型，开发者关注推理能力和 API 接入节奏。</p>
          <p>企业客户也在评估部署成本、稳定性和数据安全边界。</p>
        </article>
        <footer>ICP备案 联系我们</footer>
      </body>
    </html>
    """

    content = HtmlArticleExtractor().extract(html)

    assert "OpenAI 发布新模型" in content
    assert "企业客户" in content
    assert "ICP备案" not in content
    assert "登录 注册" not in content


def test_html_article_extractor_falls_back_to_body_text():
    html = """
    <html>
      <body>
        <div class="content">
          <p>央行发布最新货币政策报告，市场关注流动性变化。</p>
          <p>报告提到将继续保持政策稳定性和连续性。</p>
        </div>
      </body>
    </html>
    """

    content = HtmlArticleExtractor().extract(html)

    assert "央行发布最新货币政策报告" in content
    assert len(content) > 30


def test_static_html_article_strategy_returns_detail_candidate():
    strategy = StaticHtmlArticleStrategy(
        html="<article><p>OpenAI 发布新模型，开发者关注推理能力和 API 接入节奏。</p></article>",
        strategy_name="html_article",
    )

    result = strategy.fetch(
        DetailContext(
            title="OpenAI 发布新模型",
            list_content="OpenAI 发布新模型",
            source_url="https://example.com/a",
            channel_code="36kr",
        )
    )

    assert result.strategy == "html_article"
    assert "API 接入节奏" in result.content

from crawlers.csdn import CSDNCrawler


def test_csdn_resolve_detail_prefers_html_article_content():
    crawler = CSDNCrawler()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <body>
                <article id="article_content">
                  <h1>OpenAI 发布新模型</h1>
                  <p>OpenAI 发布会上介绍了新模型、价格和开放计划。</p>
                  <p>开发者正在讨论接入方式、推理能力与部署成本。</p>
                </article>
              </body>
            </html>
            """

        return DummyResponse()

    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://blog.csdn.net/demo/article/details/123456",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "开放计划" in result.content


def test_csdn_resolve_detail_falls_back_to_list_only_when_page_is_shell_noise():
    crawler = CSDNCrawler()

    class DummyResponse:
        text = "CSDN-专业开发者社区 登录 注册 沪ICP备 营业执照"

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "异常文章",
            "content": "列表摘要",
            "source_url": "https://blog.csdn.net/demo/article/details/654321",
        }
    )

    assert result.status == "list_only"
    assert result.strategy == "list_fallback"


def test_csdn_resolve_detail_merges_article_content_with_distinct_sections():
    crawler = CSDNCrawler()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <body>
                <article id="article_content">
                  <h1>Cursor 推出新功能</h1>
                  <p>Cursor 推出新功能，开发者开始评估代码补全和 Agent 协作体验。</p>
                  <section>
                    <p>团队也在比较上下文理解、工具调用和大型仓库可用性。</p>
                  </section>
                </article>
              </body>
            </html>
            """

        return DummyResponse()

    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "Cursor 推出新功能",
            "content": "列表摘要",
            "source_url": "https://blog.csdn.net/demo/article/details/123456",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "Agent 协作体验" in result.content
    assert "大型仓库可用性" in result.content


def test_csdn_web_fallback_prefers_article_block_over_shell_text():
    crawler = CSDNCrawler()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <body>
                <div class="shell-text">CSDN-专业开发者社区 登录 注册 推荐作者 相关文章 登录后查看更多内容</div>
                <main>
                  <article>
                    <h1>OpenAI API 更新</h1>
                    <p>OpenAI API 更新后，开发者开始测试新的响应格式与工具调用能力。</p>
                    <p>团队也在评估迁移成本、兼容性和线上稳定性。</p>
                  </article>
                </main>
              </body>
            </html>
            """

        return DummyResponse()

    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "OpenAI API 更新",
            "content": "列表摘要",
            "source_url": "https://blog.csdn.net/demo/article/details/654321",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "web_fallback"
    assert "响应格式与工具调用能力" in result.content
    assert "登录后查看更多内容" not in result.content

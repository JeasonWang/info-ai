from crawlers.kr36 import Kr36Crawler


def test_kr36_resolve_detail_prefers_detail_api_content():
    crawler = Kr36Crawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "articleDetail": {
                            "articleId": "987",
                            "title": "OpenAI 发布新模型",
                            "content": "<p>OpenAI 发布会上介绍了新模型、价格和开放计划。</p><p>开发者正在讨论接入方式、训练效率与部署成本。</p>",
                            "summary": "不应该优先选中的摘要",
                        }
                    }
                }

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("不应触发网页兜底"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://36kr.com/p/987",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "部署成本" in result.content


def test_kr36_resolve_detail_uses_web_fallback_when_api_payload_is_sparse():
    crawler = Kr36Crawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "content": "",
                        "summary": "更多人关注",
                    }
                }

        return DummyResponse()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <body>
                <article class="article-content">
                  <h1>英伟达发布H200芯片</h1>
                  <p>英伟达发布H200芯片，性能进一步提升，行业开始关注训练效率。</p>
                  <p>产业侧在评估显存、训练吞吐和集群升级节奏。</p>
                </article>
              </body>
            </html>
            """

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "英伟达发布H200芯片",
            "content": "列表摘要",
            "source_url": "https://36kr.com/p/987",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "web_fallback"
    assert "集群升级节奏" in result.content


def test_kr36_resolve_detail_handles_nested_api_content_fields():
    crawler = Kr36Crawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "article": {
                            "articleContent": {
                                "content": "<p>英伟达发布H200芯片，性能进一步提升。</p><p>产业侧在评估显存、训练吞吐和集群升级节奏。</p>",
                            },
                            "summary": "不应优先使用的摘要",
                        }
                    }
                }

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("不应触发网页兜底"))

    result = crawler.resolve_detail(
        {
            "title": "英伟达发布H200芯片",
            "content": "列表摘要",
            "source_url": "https://36kr.com/p/987",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "集群升级节奏" in result.content


def test_kr36_resolve_detail_merges_api_content_with_distinct_summary():
    crawler = Kr36Crawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "articleDetail": {
                            "title": "OpenAI Agent 发布",
                            "content": "<p>OpenAI Agent 发布，开发者开始评估编排能力。</p>",
                            "summary": "团队也在关注调用成本和工具链兼容性。",
                        }
                    }
                }

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("不应触发网页兜底"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI Agent 发布",
            "content": "列表摘要",
            "source_url": "https://36kr.com/p/987",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "开发者开始评估编排能力" in result.content
    assert "调用成本和工具链兼容性" in result.content


def test_kr36_web_fallback_prefers_article_block_over_shell_text():
    crawler = Kr36Crawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {"data": {"summary": "简短摘要"}}

        return DummyResponse()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <body>
                <div class="shell-text">
                  登录后查看更多内容 36氪 频道推荐 热门资讯 登录后查看更多内容
                </div>
                <article>
                  <h1>Anthropic 发布新模型</h1>
                  <div class="article-content">
                    <p>Anthropic 发布新模型，开发者开始比较上下文窗口和工具调用能力。</p>
                    <p>企业客户同时关注定价、延迟与生产可用性。</p>
                  </div>
                </article>
              </body>
            </html>
            """

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "Anthropic 发布新模型",
            "content": "列表摘要",
            "source_url": "https://36kr.com/p/654",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "web_fallback"
    assert "上下文窗口和工具调用能力" in result.content
    assert "登录后查看更多内容" not in result.content

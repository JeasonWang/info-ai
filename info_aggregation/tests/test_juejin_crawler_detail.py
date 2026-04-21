from crawlers.juejin import JuejinCrawler


def test_juejin_resolve_detail_prefers_detail_api_markdown_content():
    crawler = JuejinCrawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "article_info": {
                            "article_id": "123",
                            "title": "OpenAI 发布新模型",
                            "mark_content": "OpenAI 发布新模型，重点介绍推理能力、价格变化与开放计划。开发者正在讨论接入方式和部署成本。",
                            "content": "<p>不应该被优先选择的 HTML 内容</p>",
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
            "source_url": "https://juejin.cn/post/123",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "部署成本" in result.content


def test_juejin_resolve_detail_uses_web_fallback_when_api_content_is_weak():
    crawler = JuejinCrawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "article_info": {
                            "article_id": "123",
                            "title": "讨论继续",
                            "mark_content": "更多人关注",
                            "content": "",
                        }
                    }
                }

        return DummyResponse()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <body>
                <article>
                  <h1>OpenAI 发布新模型</h1>
                  <p>OpenAI 发布新模型，现场重点包括推理能力、价格方案和开发者接入计划。</p>
                  <p>多位开发者补充了接入方式与部署成本的讨论。</p>
                </article>
              </body>
            </html>
            """

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://juejin.cn/post/123",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "web_fallback"
    assert "开发者接入计划" in result.content


def test_juejin_resolve_detail_merges_markdown_and_html_content():
    crawler = JuejinCrawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "article_info": {
                            "article_id": "123",
                            "title": "Cursor 推出新功能",
                            "mark_content": "Cursor 推出新功能，开发者开始评估代码补全和 Agent 协作体验。",
                            "content": "<p>团队也在比较上下文理解、工具调用和大型仓库可用性。</p>",
                        }
                    }
                }

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("不应触发网页兜底"))

    result = crawler.resolve_detail(
        {
            "title": "Cursor 推出新功能",
            "content": "列表摘要",
            "source_url": "https://juejin.cn/post/123",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "Agent 协作体验" in result.content
    assert "上下文理解、工具调用" in result.content


def test_juejin_web_fallback_prefers_article_block_over_shell_text():
    crawler = JuejinCrawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {
                    "data": {
                        "article_info": {
                            "article_id": "123",
                            "title": "OpenAI API 更新",
                            "mark_content": "更多人关注",
                            "content": "",
                        }
                    }
                }

        return DummyResponse()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <body>
                <div class="shell-text">登录 掘金首页 推荐作者 相关文章 登录后查看更多内容</div>
                <article>
                  <h1>OpenAI API 更新</h1>
                  <p>OpenAI API 更新后，开发者开始测试新的响应格式与工具调用能力。</p>
                  <p>团队也在评估迁移成本、兼容性和线上稳定性。</p>
                </article>
              </body>
            </html>
            """

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "OpenAI API 更新",
            "content": "列表摘要",
            "source_url": "https://juejin.cn/post/123",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "web_fallback"
    assert "响应格式与工具调用能力" in result.content
    assert "登录后查看更多内容" not in result.content

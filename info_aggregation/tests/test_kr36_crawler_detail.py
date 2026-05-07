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

    assert result.status in {"complete", "partial"}
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

    assert result.status in {"complete", "partial"}
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

    assert result.status in {"complete", "partial"}
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

    assert result.status in {"complete", "partial"}
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

    assert result.status in {"complete", "partial"}
    assert result.strategy == "web_fallback"
    assert "上下文窗口和工具调用能力" in result.content
    assert "登录后查看更多内容" not in result.content


def test_kr36_web_fallback_rejects_captcha_challenge_page():
    crawler = Kr36Crawler()

    def fake_post(url, data=None, headers=None, timeout=None):
        class DummyResponse:
            def json(self):
                return {"data": {"summary": ""}}

        return DummyResponse()

    def fake_fetch(url, headers=None, timeout=None, params=None):
        class DummyResponse:
            text = """
            <html>
              <head><script src="https://lf-cdn-tos.bytescm.com/obj/static/sec_sdk_build/3.3.4/captcha/index.js"></script></head>
              <body>captchaOptions showMode 验证后继续访问</body>
            </html>
            """

        return DummyResponse()

    crawler.session.post = fake_post
    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "苹果悄悄砍掉丐版Mac mini",
            "content": "列表摘要",
            "source_url": "https://36kr.com/p/3792125638352134",
        }
    )

    assert result.status == "list_only"
    assert result.strategy == "list_fallback"


def test_kr36_google_news_index_restores_real_leads_when_primary_entries_fail():
    crawler = Kr36Crawler()

    class DummyResponse:
        text = """
        <rss><channel>
          <item>
            <title>AI 公司完成新一轮融资 - 36氪</title>
            <link>https://news.google.com/rss/articles/example</link>
            <source>36氪</source>
            <description><![CDATA[<a href="https://news.google.com/rss/articles/example">AI 公司完成新一轮融资</a>&nbsp;&nbsp;<font color="#6f6f6f">36氪</font>]]></description>
          </item>
          <item>
            <title>其它来源新闻</title>
            <link>https://example.com/story</link>
            <source>其它</source>
            <description>Not 36kr</description>
          </item>
        </channel></rss>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    items = crawler._crawl_google_news_index()

    assert len(items) == 1
    assert items[0]["title"] == "AI 公司完成新一轮融资"
    assert items[0]["_kr36_source"] == "google_news_index"


def test_kr36_api_uses_nested_partner_payload_and_template_material():
    crawler = Kr36Crawler()
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["data"] = data

        class DummyResponse:
            def json(self):
                return {
                    "code": 0,
                    "data": {
                        "hotRankList": [
                            {
                                "itemId": 123,
                                "publishTime": 1777690270108,
                                "templateMaterial": {
                                    "widgetTitle": "DeepSeek 大更新",
                                    "summary": "视觉能力升级，开发者开始测试多模态任务。",
                                    "authorName": "36氪",
                                    "statRead": 24655,
                                    "statCollect": 73,
                                    "statComment": 12,
                                    "statPraise": 138,
                                },
                            }
                        ]
                    },
                }

        return DummyResponse()

    crawler.session.post = fake_post

    items = crawler._crawl_api()

    assert '"partner_id": "wap"' in captured["data"]
    assert '"param"' in captured["data"]
    assert items[0]["source_url"] == "https://www.36kr.com/p/123"
    assert "阅读24655" in items[0]["content"]
    assert "评论12" in items[0]["content"]


def test_kr36_web_fallback_extracts_widget_content_from_initial_state():
    crawler = Kr36Crawler()

    html = """
    <html><body>
      <script async>
      window.initialState={
        "articleDetail":{
          "articleDetailData":{
            "data":{
              "widgetTitle":"续集没翻车",
              "summary":"当时尚大刊也被降本增效。",
              "widgetContent":"<p>作者 | 易天天</p><p>再次回到电影片场，演员和制作团队面临预算收缩。</p><p>文章分析了传统媒体、时尚品牌和影视制作在 AI 时代的成本压力。</p><p>公司需要重新评估商业模式、内容生产节奏和用户付费意愿。</p>"
            }
          }
        }
      };
      </script>
    </body></html>
    """

    content = crawler._extract_web_fallback_content(html, "续集没翻车")

    assert "预算收缩" in content
    assert "商业模式" in content

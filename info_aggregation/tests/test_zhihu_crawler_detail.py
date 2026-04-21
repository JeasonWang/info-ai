from crawlers.zhihu import ZhihuCrawler


def test_zhihu_resolve_detail_prefers_answer_api_content(monkeypatch):
    crawler = ZhihuCrawler()

    def fake_fetch_json(url, **kwargs):
        assert "api/v4/questions/123456/answers" in url
        return {
            "data": [
                {
                    "content": "<p>回答详细解释了 AI Agent 在多步骤任务执行中的规划、工具调用、上下文管理方式，以及在复杂任务里如何拆解步骤并调用外部能力。</p>",
                    "excerpt": "回答摘要",
                }
            ]
        }

    monkeypatch.setattr(crawler, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(crawler, "fetch", lambda *args, **kwargs: None)

    result = crawler.resolve_detail(
        {
            "title": "AI Agent 技术路线",
            "content": "列表摘要",
            "source_url": "https://www.zhihu.com/question/123456",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "answer_api"
    assert "工具调用、上下文管理方式" in result.content


def test_zhihu_resolve_detail_falls_back_to_web_page(monkeypatch):
    crawler = ZhihuCrawler()

    class DummyResponse:
        text = """
        <html><body>
          <div class="RichContent-inner">
            页面内容介绍了 MCP、API 编排与开发工具接入方式，并总结了实践经验、上下文管理方法以及工具链协同落地时的关键注意事项。
          </div>
        </body></html>
        """

    monkeypatch.setattr(crawler, "fetch_json", lambda *args, **kwargs: {"data": []})
    monkeypatch.setattr(crawler, "fetch", lambda *args, **kwargs: DummyResponse())

    result = crawler.resolve_detail(
        {
            "title": "MCP 工具链实践",
            "content": "列表摘要",
            "source_url": "https://www.zhihu.com/question/654321",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "开发工具接入方式" in result.content


def test_zhihu_resolve_detail_merges_multiple_answers_without_duplicates(monkeypatch):
    crawler = ZhihuCrawler()

    def fake_fetch_json(url, **kwargs):
        return {
            "data": [
                {
                    "content": "<p>第一条回答解释了 OpenAI API 的接入方式、上下文管理和工具调用节奏。</p>",
                    "excerpt": "第一条摘要",
                },
                {
                    "content": "<p>第一条回答解释了 OpenAI API 的接入方式、上下文管理和工具调用节奏。</p>",
                    "excerpt": "重复摘要",
                },
                {
                    "content": "",
                    "excerpt": "第二条回答补充了开发工具集成、自动化测试以及发布流程中的注意事项，帮助团队更快落地。",
                },
            ]
        }

    monkeypatch.setattr(crawler, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(crawler, "fetch", lambda *args, **kwargs: None)

    result = crawler.resolve_detail(
        {
            "title": "OpenAI API 开发实践",
            "content": "列表摘要",
            "source_url": "https://www.zhihu.com/question/987654",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "answer_api"
    assert result.content.count("OpenAI API 的接入方式") == 1
    assert "开发工具集成" in result.content

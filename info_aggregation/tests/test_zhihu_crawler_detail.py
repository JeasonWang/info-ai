from crawlers.zhihu import ZhihuCrawler


def test_zhihu_cookie_can_be_loaded_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("ZHIHU_COOKIE", raising=False)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "OTHER=value\nZHIHU_COOKIE=z_c0=session-token; d_c0=device-token\n",
        encoding="utf-8",
    )
    crawler = ZhihuCrawler()

    assert crawler._get_zhihu_cookie() == "z_c0=session-token; d_c0=device-token"


def test_zhihu_cookie_parser_builds_browser_cookie_jar():
    crawler = ZhihuCrawler()

    cookies = crawler._parse_cookie_jar("z_c0=session-token; d_c0=device-token")

    assert cookies == [
        {"name": "z_c0", "value": "session-token", "domain": ".zhihu.com", "path": "/"},
        {"name": "d_c0", "value": "device-token", "domain": ".zhihu.com", "path": "/"},
    ]


def test_zhihu_headers_include_configured_cookie(monkeypatch):
    monkeypatch.setenv("ZHIHU_COOKIE", "z_c0=session-token; d_c0=device-token")
    monkeypatch.setenv("ZHIHU_ZSE_93", "101_3_3.0")
    monkeypatch.setenv("ZHIHU_ZSE_96", "2.0_signature")
    crawler = ZhihuCrawler()

    headers = crawler._build_zhihu_headers("https://www.zhihu.com/hot")

    assert headers["Cookie"] == "z_c0=session-token; d_c0=device-token"
    assert headers["Referer"] == "https://www.zhihu.com/hot"
    assert headers["x-zse-93"] == "101_3_3.0"
    assert headers["x-zse-96"] == "2.0_signature"


def test_zhihu_crawl_uses_hot_search_api_when_available(monkeypatch):
    crawler = ZhihuCrawler()

    def fake_fetch_json(url, **kwargs):
        if "api/v4/search/hot_search" in url:
            return {
                "hot_search_queries": [
                    {
                        "query": "AI Agent 最新进展",
                        "real_query": "AI Agent 最新进展",
                        "hot_show": "128 万",
                    }
                ]
            }
        if "api/v4/search_v3" in url:
            return {"data": []}
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(crawler, "fetch_json", fake_fetch_json)

    items = crawler._crawl_hot_search_api()

    assert items[0]["title"] == "AI Agent 最新进展"
    assert items[0]["source_url"] == "https://www.zhihu.com/search?type=content&q=AI%20Agent%20%E6%9C%80%E6%96%B0%E8%BF%9B%E5%B1%95"
    assert items[0]["_query_word"] == "AI Agent 最新进展"
    assert items[0]["indicator_value"] == "128 万"


def test_zhihu_hot_search_enriches_question_from_search_v3(monkeypatch):
    crawler = ZhihuCrawler()

    def fake_fetch_json(url, **kwargs):
        if "api/v4/search/hot_search" in url:
            return {"hot_search_queries": [{"query": "微信朋友圈改版", "hot_show": "500 万"}]}
        if "api/v4/search_v3" in url:
            return {
                "data": [
                    {
                        "type": "hot_timing",
                        "object": {
                            "description": {
                                "object": {
                                    "id": "2032722050247124724",
                                    "type": "question",
                                    "title": "<em>微信朋友圈改版</em>，你喜欢这个新样式吗？",
                                    "description": "4月28日，话题引发热议。腾讯客服表示文字位置变化可能是展示形式的优化调整。",
                                    "answer_count": 130,
                                    "visits_count": 596250,
                                }
                            }
                        },
                    }
                ]
            }
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(crawler, "fetch_json", fake_fetch_json)

    item = crawler._crawl_hot_search_api()[0]

    assert item["title"] == "微信朋友圈改版，你喜欢这个新样式吗？"
    assert item["source_url"] == "https://www.zhihu.com/question/2032722050247124724"
    assert item["source_id"] == "b2fca120360c1d07"
    assert "腾讯客服表示" in item["content"]
    assert item["_search_content"] == item["content"]


def test_zhihu_embedded_search_content_can_be_used_as_detail(monkeypatch):
    crawler = ZhihuCrawler()
    monkeypatch.setattr(crawler, "fetch_json", lambda *args, **kwargs: {"data": []})
    monkeypatch.setattr(crawler, "fetch", lambda *args, **kwargs: None)

    result = crawler.resolve_detail(
        {
            "title": "微信朋友圈改版，你喜欢这个新样式吗？",
            "content": "列表摘要",
            "_search_content": "微信朋友圈改版后，文字描述从配图右侧移至上方，并新增时间轴浏览功能。腾讯客服回应称这是展示形式优化调整，用户可以继续反馈体验。",
            "source_url": "https://www.zhihu.com/question/2032722050247124724",
        }
    )

    assert result.status in {"complete", "partial"}
    assert result.strategy == "search_embedded"
    assert "时间轴浏览功能" in result.content


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

    assert result.status in {"complete", "partial"}
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

    assert result.status in {"complete", "partial"}
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

    assert result.status in {"complete", "partial"}
    assert result.strategy == "answer_api"
    assert result.content.count("OpenAI API 的接入方式") == 1
    assert "开发工具集成" in result.content


def test_zhihu_answer_api_prefers_high_vote_and_informative_answers(monkeypatch):
    crawler = ZhihuCrawler()

    def fake_fetch_json(url, **kwargs):
        assert "include=data%5B%2A%5D.content" in url
        return {
            "data": [
                {
                    "content": "<p>短回答。</p>",
                    "voteup_count": 999,
                },
                {
                    "content": "<p>低赞但很长的回答，介绍了大模型应用在企业知识库、客服自动化和代码生成中的落地方式，也说明了评估指标、风险控制和数据治理要求。</p>",
                    "voteup_count": 5,
                },
                {
                    "content": "<p>高赞回答详细分析了 AI Agent 的任务规划、工具调用、长期记忆、失败重试和人工校验流程，适合作为事件分析的主体材料。</p>",
                    "voteup_count": 88,
                },
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

    assert result.status in {"complete", "partial"}
    assert result.strategy == "answer_api"
    assert result.content.startswith("高赞回答详细分析")
    assert "短回答" not in result.content
    assert "数据治理要求" in result.content


def test_zhihu_resolve_detail_uses_rendered_question_when_api_is_unavailable(monkeypatch):
    crawler = ZhihuCrawler(
        rendered_fetcher=lambda url: """
        知乎
        AI Agent 技术路线
        3 个回答
        默认排序
        回答详细介绍了 AI Agent 如何把复杂任务拆成多个步骤，并在执行过程中结合工具调用、记忆管理、任务反思和结果校验。
        在真实工程里，Agent 需要明确目标、选择工具、跟踪上下文，并在失败后重新规划，这些能力决定了复杂任务的完成质量。
        编辑于 2026-04-30
        赞同 42
        添加评论
        """
    )

    monkeypatch.setattr(crawler, "fetch_json", lambda *args, **kwargs: {"data": []})
    monkeypatch.setattr(crawler, "fetch", lambda *args, **kwargs: None)

    result = crawler.resolve_detail(
        {
            "title": "AI Agent 技术路线",
            "content": "列表摘要",
            "source_url": "https://www.zhihu.com/question/123456",
        }
    )

    assert result.status in {"complete", "partial"}
    assert result.strategy == "rendered_question"
    assert "任务反思和结果校验" in result.content
    assert "添加评论" not in result.content


def test_zhihu_rendered_login_wall_is_rejected():
    crawler = ZhihuCrawler()

    cleaned = crawler._clean_rendered_text(
        """
        打开知乎App
        验证码登录密码登录
        中国 +86
        获取短信验证码
        登录/注册
        知乎专栏圆桌发现移动应用
        """,
        "AI Agent 技术路线",
    )

    assert cleaned == ""

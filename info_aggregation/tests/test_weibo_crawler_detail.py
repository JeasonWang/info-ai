from crawlers.weibo import WeiboCrawler


def test_weibo_resolve_detail_prefers_topic_search_content():
    crawler = WeiboCrawler()

    def fake_fetch_json(url, headers=None):
        if "ajax/search/topic" in url:
            return {
                "data": {
                    "statuses": [
                        {"text": "OpenAI 发布新模型，重点介绍推理、价格和开放计划。"},
                        {"text": "开发者讨论接入方式，现场信息持续更新。"},
                    ]
                }
            }
        if "ajax/statuses/hot_band" in url:
            return {
                "data": {
                    "band_list": [
                        {
                            "word": "OpenAI 发布新模型",
                            "note": "热搜背景",
                            "raw_text": "热榜扩展信息",
                            "desc": "更多讨论",
                        }
                    ]
                }
            }
        if "m.weibo.cn/api/container/getIndex" in url:
            return {"data": {"cards": []}}
        return {}

    crawler.fetch_json = fake_fetch_json

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://s.weibo.com/weibo?q=%23OpenAI 发布新模型%23",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert "新模型" in result.content


def test_weibo_resolve_detail_falls_back_to_list_only_when_all_strategies_fail():
    crawler = WeiboCrawler()
    crawler.fetch_json = lambda *args, **kwargs: {}

    result = crawler.resolve_detail(
        {
            "title": "异常热搜",
            "content": "仅有列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "list_only"
    assert result.strategy == "list_fallback"


def test_weibo_resolve_detail_uses_hot_band_when_topic_search_is_blocked():
    crawler = WeiboCrawler()

    def fake_fetch_json(url, headers=None):
        if "ajax/search/topic" in url:
            return {
                "data": {
                    "statuses": [
                        {"text": "请先登录后查看更多内容"},
                    ]
                }
            }
        if "ajax/statuses/hot_band" in url:
            return {
                "data": {
                    "band_list": [
                        {
                            "word": "异常热搜",
                            "note": "热搜背景说明",
                            "raw_text": "话题正在持续升温",
                            "desc": "多平台讨论焦点",
                        }
                    ]
                }
            }
        if "m.weibo.cn/api/container/getIndex" in url:
            return {"data": {"cards": []}}
        return {}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "异常热搜",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "hot_band_context"
    assert "热搜背景说明" in result.content


def test_weibo_resolve_detail_deduplicates_repeated_topic_statuses():
    crawler = WeiboCrawler()

    def fake_fetch_json(url, headers=None):
        if "ajax/search/topic" in url:
            return {
                "data": {
                    "statuses": [
                        {"text": "<a>OpenAI</a> 发布新模型，重点介绍推理、价格和开放计划。"},
                        {"text": "OpenAI 发布新模型，重点介绍推理、价格和开放计划。"},
                        {"text": "开发者讨论接入方式，现场信息持续更新。"},
                    ]
                }
            }
        if "ajax/statuses/hot_band" in url or "m.weibo.cn/api/container/getIndex" in url:
            return {"data": {"band_list": [], "cards": []}}
        return {}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "complete"
    assert result.content.count("OpenAI 发布新模型") == 1
    assert "开发者讨论接入方式" in result.content


def test_weibo_resolve_detail_prefers_mobile_search_when_topic_search_is_weak():
    crawler = WeiboCrawler()

    def fake_fetch_json(url, headers=None):
        if "ajax/search/topic" in url:
            return {
                "data": {
                    "statuses": [
                        {"text": "今晚讨论继续。"},
                    ]
                }
            }
        if "m.weibo.cn/api/container/getIndex" in url:
            return {
                "data": {
                    "cards": [
                        {"mblog": {"text": "OpenAI 发布新模型，现场重点包括推理能力、价格方案和开发者接入计划。"}},
                        {"mblog": {"text": "多位用户补充了发布会细节，并讨论开放时间表。"}},
                    ]
                }
            }
        if "ajax/statuses/hot_band" in url:
            return {"data": {"band_list": []}}
        return {}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "mobile_search"
    assert "开发者接入计划" in result.content


def test_weibo_resolve_detail_marks_failed_when_only_login_and_shell_noise_exist():
    crawler = WeiboCrawler()

    def fake_fetch_json(url, headers=None):
        if "ajax/search/topic" in url:
            return {"data": {"statuses": [{"text": "请先登录后查看更多内容"}]}}
        if "ajax/statuses/hot_band" in url:
            return {"data": {"band_list": []}}
        if "m.weibo.cn/api/container/getIndex" in url:
            return {
                "data": {
                    "cards": [
                        {"mblog": {"text": "微博正文 请先登录，登录注册更精彩"}},
                    ]
                }
            }
        return {}

    class DummyResponse:
        text = "微博-随时随地发现新鲜事 超话社区 热门微博 视频 图片 登录 注册"

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "异常热搜",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "failed"
    assert result.failure_reason in {"anti_crawl_blocked", "shell_page"}


def test_weibo_mobile_search_merges_long_text_and_retweet_content():
    crawler = WeiboCrawler()

    def fake_fetch_json(url, headers=None):
        if "ajax/search/topic" in url:
            return {"data": {"statuses": []}}
        if "ajax/statuses/hot_band" in url:
            return {"data": {"band_list": []}}
        if "m.weibo.cn/api/container/getIndex" in url:
            return {
                "data": {
                    "cards": [
                        {
                            "mblog": {
                                "text": "OpenAI 发布新模型，基础介绍。全文",
                                "longText": {
                                    "longTextContent": "OpenAI 发布新模型，基础介绍。详细内容包括推理能力、价格变化与开放计划。"
                                },
                                "retweeted_status": {
                                    "text": "转发补充：开发者开始讨论接入方式和成本变化。",
                                },
                            }
                        }
                    ]
                }
            }
        return {}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "mobile_search"
    assert "价格变化与开放计划" in result.content
    assert "开发者开始讨论接入方式和成本变化" in result.content


def test_weibo_topic_search_merges_long_text_and_retweet_content():
    crawler = WeiboCrawler()

    def fake_fetch_json(url, headers=None):
        if "ajax/search/topic" in url:
            return {
                "data": {
                    "statuses": [
                        {
                            "text": "OpenAI 发布新模型，基础介绍。全文",
                            "longText": {
                                "longTextContent": "OpenAI 发布新模型，详细内容包括推理能力增强、价格调整和开放时间表。"
                            },
                            "retweeted_status": {
                                "text": "转发补充：开发者关注 API 接入方式、成本变化和推理速度表现。"
                            },
                        }
                    ]
                }
            }
        if "ajax/statuses/hot_band" in url:
            return {"data": {"band_list": []}}
        if "m.weibo.cn/api/container/getIndex" in url:
            return {"data": {"cards": []}}
        return {}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert "价格调整和开放时间表" in result.content
    assert "API 接入方式、成本变化和推理速度表现" in result.content


def test_weibo_web_fallback_extracts_relevant_article_block():
    crawler = WeiboCrawler()
    crawler.fetch_json = lambda *args, **kwargs: {"data": {"statuses": [], "band_list": [], "cards": []}}

    class DummyResponse:
        text = """
        <html>
          <body>
            <nav>微博 超话社区 热门微博 视频 图片 登录 注册</nav>
            <article>
              <h1>OpenAI 发布新模型</h1>
              <p>OpenAI 发布新模型后，外界开始关注推理能力、价格变化和开放节奏。</p>
              <p>多位开发者补充了接入方式、调用成本和上线时间表。</p>
            </article>
          </body>
        </html>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.strategy == "web_fallback"
    assert result.status == "complete"
    assert "推理能力、价格变化和开放节奏" in result.content


def test_weibo_web_fallback_ignores_navigation_shell_noise():
    crawler = WeiboCrawler()
    crawler.fetch_json = lambda *args, **kwargs: {"data": {"statuses": [], "band_list": [], "cards": []}}

    class DummyResponse:
        text = """
        <html>
          <body>
            <div>微博-随时随地发现新鲜事</div>
            <div>超话社区 热门微博 视频 图片 登录 注册</div>
            <div>话题讨论页，查看更多内容请先登录</div>
          </body>
        </html>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "异常热搜",
            "content": "列表摘要",
            "source_url": "https://example.com",
        }
    )

    assert result.status == "failed"
    assert result.failure_reason in {"shell_page", "anti_crawl_blocked"}

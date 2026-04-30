from crawlers.toutiao import ToutiaoCrawler


def test_toutiao_crawl_preserves_real_hot_board_url_and_query_word():
    crawler = ToutiaoCrawler()

    crawler.fetch_json = lambda *args, **kwargs: {
        "data": [
            {
                "ClusterId": "12345",
                "Title": "榴莲价格大降",
                "HotDesc": "",
                "Label": "hot",
                "QueryWord": "榴莲 价格",
                "Url": "https://www.toutiao.com/trending/12345/?category_name=topic_innerflow",
                "Image": {"url": "https://example.com/durian.png"},
                "InterestCategory": ["财经", "消费"],
            }
        ]
    }

    items = crawler.crawl()

    assert len(items) == 1
    assert items[0]["source_url"] == "https://www.toutiao.com/trending/12345/?category_name=topic_innerflow"
    assert items[0]["_query_word"] == "榴莲 价格"
    assert items[0]["_image_url"] == "https://example.com/durian.png"
    assert items[0]["_interest_category"] == ["财经", "消费"]


def test_toutiao_hot_board_detail_rejects_title_and_label_only_payload():
    crawler = ToutiaoCrawler()

    crawler.fetch_json = lambda *args, **kwargs: {
        "data": [
            {
                "ClusterId": "12345",
                "Title": "榴莲价格大降",
                "HotDesc": "",
                "Abstract": "",
                "Label": "hot",
            }
        ]
    }

    result = crawler._fetch_hot_board_detail(
        {
            "title": "榴莲价格大降",
            "content": "榴莲价格大降。hot",
            "source_url": "https://www.toutiao.com/trending/12345/",
            "_cluster_id": "12345",
        }
    )

    assert result is None


def test_toutiao_resolve_detail_prefers_hot_board_detail_content():
    crawler = ToutiaoCrawler()

    def fake_fetch_json(url, headers=None):
        if "hot-board" in url and "cluster_id=12345" in url:
            return {
                "data": [
                    {
                        "ClusterId": "12345",
                        "Title": "英伟达发布H200芯片",
                        "HotDesc": "H200 芯片性能进一步提升，行业开始关注训练效率。",
                        "Abstract": "多家厂商讨论显存、训练速度、部署成本与新一代集群升级节奏。",
                        "Label": "芯片",
                    }
                ]
            }
        if "api/search/content" in url:
            return {"data": []}
        return {"data": []}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "英伟达发布H200芯片",
            "content": "列表摘要",
            "source_url": "https://www.toutiao.com/trending/12345/",
            "_cluster_id": "12345",
            "_hot_desc": "H200 芯片性能进一步提升，行业开始关注训练效率。",
            "_label": "芯片",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "hot_board_detail"
    assert "训练速度" in result.content


def test_toutiao_resolve_detail_uses_search_when_hot_board_detail_is_weak():
    crawler = ToutiaoCrawler()

    def fake_fetch_json(url, headers=None):
        if "hot-board" in url and "cluster_id=12345" in url:
            return {
                "data": [
                    {
                        "ClusterId": "12345",
                        "Title": "讨论继续",
                        "HotDesc": "更多人关注",
                        "Abstract": "",
                        "Label": "",
                    }
                ]
            }
        if "api/search/content" in url:
            return {
                "data": [
                    {
                        "title": "英伟达发布H200芯片",
                        "abstract": "H200芯片带来更高训练吞吐，开发者开始评估显存配置、部署成本和交付节奏。",
                    },
                    {
                        "title": "行业观察",
                        "content": "产业链继续讨论新一代 GPU 在大模型训练中的升级窗口。",
                    },
                ]
            }
        return {"data": []}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "英伟达发布H200芯片",
            "content": "列表摘要",
            "source_url": "https://www.toutiao.com/trending/12345/",
            "_cluster_id": "12345",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "search_content"
    assert "部署成本" in result.content


def test_toutiao_search_content_deduplicates_and_keeps_useful_context():
    crawler = ToutiaoCrawler()

    def fake_fetch_json(url, headers=None):
        if "hot-board" in url and "cluster_id=67890" in url:
            return {
                "data": [
                    {
                        "ClusterId": "67890",
                        "Title": "持续发酵",
                        "HotDesc": "关注增加",
                        "Abstract": "",
                        "Label": "",
                    }
                ]
            }
        if "api/search/content" in url:
            return {
                "data": [
                    {
                        "title": "OpenAI API 发布新能力",
                        "abstract": "OpenAI API 发布新能力，开发者开始讨论上下文长度、工具调用和部署成本。",
                    },
                    {
                        "title": "OpenAI API 发布新能力",
                        "content": "OpenAI API 发布新能力，开发者开始讨论上下文长度、工具调用和部署成本。",
                    },
                    {
                        "title": "工程实践",
                        "content": "团队继续补充自动化测试、监控治理与发布流程建议，帮助能力更快落地。",
                    },
                ]
            }
        return {"data": []}

    crawler.fetch_json = fake_fetch_json
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not hit web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI API 发布新能力",
            "content": "列表摘要",
            "source_url": "https://www.toutiao.com/trending/67890/",
            "_cluster_id": "67890",
            "_hot_desc": "OpenAI API 发布新能力",
            "_label": "API",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "search_content"
    assert result.content.count("OpenAI API 发布新能力") == 1
    assert "自动化测试" in result.content


def test_toutiao_web_fallback_prefers_article_blocks():
    crawler = ToutiaoCrawler()

    class DummyResponse:
        text = """
        <html><body>
          <nav>首页 导航 登录</nav>
          <article>
            <h1>OpenAI API 发布新能力</h1>
            <p>正文详细介绍了新能力的开放范围、开发者接入方式、部署建议和自动化治理要点。</p>
          </article>
        </body></html>
        """

    crawler.fetch_json = lambda *args, **kwargs: {"data": []}
    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "OpenAI API 发布新能力",
            "content": "列表摘要",
            "source_url": "https://www.toutiao.com/trending/99999/",
            "_cluster_id": "99999",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "web_fallback"
    assert "部署建议和自动化治理要点" in result.content


def test_toutiao_resolve_detail_uses_rendered_page_when_static_page_is_shell():
    crawler = ToutiaoCrawler(
        rendered_fetcher=lambda url: """
        榴莲价格大降
        今年榴莲主产区供应增加，进口到港量持续提升，批发市场和商超价格同步回落。
        多地消费者反馈价格比去年同期明显下降，水果商家也开始通过促销提升周转。
        业内人士认为，短期价格仍会受成熟度、物流和产地天气影响。
        """
    )

    class DummyResponse:
        text = "<html><body>今日头条 您需要允许该网站执行 JavaScript</body></html>"

    crawler.fetch_json = lambda *args, **kwargs: {"data": []}
    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "榴莲价格大降",
            "content": "榴莲价格大降",
            "source_url": "https://www.toutiao.com/trending/7633236449026424858/",
            "_cluster_id": "7633236449026424858",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "rendered_page"
    assert result.score >= 80
    assert "进口到港量持续提升" in result.content


def test_toutiao_rendered_text_removes_navigation_and_comment_sections():
    crawler = ToutiaoCrawler()

    cleaned = crawler._clean_rendered_text(
        """
        关注 推荐 长沙 视频 财经 科技 热点 国际 更多 搜索 消息 发布
        96岁奶奶回应10年还清2077万债务
        热门事件阅读量32万
        事件详情
        浙江96岁奶奶摆摊10年还清2077万元债务，“我不过是守住了做人的底线”
        96岁的陈金英，53岁退休后创业做羽绒服，靠着诚信经营把厂子做到年产值千万。
        结果81岁那年，企业资金链断裂，一下子欠下2077万。
        身边人都劝她申请破产，法律上完全行得通。可老太太一口拒绝。
        分享
        另一位作者1小时前
        第二篇长文不应该混入第一篇正文，否则会让事件分析引用多篇不同立场内容。
        网友讨论
        神秘可乐Jmy 303 厂房存货卖了2050万
        """
    )

    assert not cleaned.startswith("关注 推荐")
    assert "事件详情" not in cleaned
    assert "网友讨论" not in cleaned
    assert "靠着诚信经营把厂子做到年产值千万" in cleaned
    assert "第二篇长文" not in cleaned
    assert "神秘可乐" not in cleaned


def test_toutiao_rendered_text_extracts_article_page_body_only():
    crawler = ToutiaoCrawler()

    cleaned = crawler._clean_rendered_text(
        """
        搜索
        消息
        发布
        登录
        354
        评论
        收藏
        分享
        致敬每一双创造美好的劳动之手
        2026-04-29 16:44·人民日报
        你有仔细观察过劳动者的手吗？万千双手孕育生机，温暖山河缔造不凡。正是这一双双手，耕耘出幸福的生活，铸就起时代的丰碑。“五一”国际劳动节将至，致敬每一双创造美好的劳动之手，致敬为美好生活努力奋斗的劳动者！
        举报
        评论 0
        请先 登录 后发表评论～
        热门：贾百立的独白暗区无限马尾发小跟班
        人民日报
        """
    )

    assert "万千双手孕育生机" in cleaned
    assert "2026-04-29" not in cleaned
    assert "热门：" not in cleaned
    assert "请先 登录" not in cleaned


def test_toutiao_web_fallback_rejects_javascript_shell_page():
    crawler = ToutiaoCrawler()

    class DummyResponse:
        text = "<html><body>今日头条 您需要允许该网站执行 JavaScript</body></html>"

    crawler.fetch_json = lambda *args, **kwargs: {"data": []}
    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "机器人半马见证大国创造澎湃动能",
            "content": "机器人半马见证大国创造澎湃动能 标签：hot",
            "source_url": "https://www.toutiao.com/trending/7630373183060770879/",
            "_cluster_id": "7630373183060770879",
        }
    )

    assert result.strategy == "list_fallback"
    assert result.content != "今日头条 您需要允许该网站执行 JavaScript"

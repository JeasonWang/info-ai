from crawlers.toutiao import ToutiaoCrawler


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

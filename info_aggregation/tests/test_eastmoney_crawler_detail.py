import json

from crawlers.eastmoney import EastmoneyCrawler


def test_eastmoney_resolve_detail_combines_indicator_and_related_news():
    crawler = EastmoneyCrawler()

    class SearchResponse:
        text = "jQuery(" + json.dumps(
            {
                "result": {
                    "cmsArticleWebOld": {
                        "list": [
                            {
                                "title": "国际金价震荡走强",
                                "content": "国际金价受到美元指数回落和避险需求升温影响，市场继续关注美联储政策预期变化。",
                                "description": "黄金市场短期仍受通胀数据、实际利率和央行购金节奏影响。",
                                "url": "",
                            },
                            {
                                "title": "贵金属市场观察",
                                "content": "投资者关注美国就业数据和地缘风险，若风险偏好下降，黄金走势可能保持偏强震荡。",
                                "description": "机构建议关注仓位控制和宏观数据发布节奏。",
                                "url": "",
                            },
                        ]
                    }
                }
            },
            ensure_ascii=False,
        ) + ")"

    crawler.fetch = lambda *args, **kwargs: SearchResponse()

    result = crawler.resolve_detail(
        {
            "title": "国际金价: 2350.20美元/盎司 ↑12.50",
            "content": "国际金价当前报2350.20美元/盎司，上涨12.50美元，更新时间2026-05-02 17:00。数据来源：东方财富网实时行情。",
            "source_url": "https://quote.eastmoney.com/",
            "indicator_name": "国际金价",
            "indicator_value": "2350.20美元/盎司",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "eastmoney_market_context"
    assert "美元指数回落" in result.content
    assert "2350.20美元/盎司" in result.content

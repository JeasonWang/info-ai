from services.collection.detail_pipeline import DetailStrategyResult, get_channel_detail_profile, run_detail_pipeline
from crawlers.base import BaseCrawler


class LongContentCrawler(BaseCrawler):
    """测试用爬虫，模拟渠道已经抓到完整详情正文。"""

    def __init__(self, detail_content: str):
        super().__init__("long_content_test", "长正文测试")
        self.detail_content = detail_content

    def crawl(self) -> list:
        return []

    def fetch_detail(self, source_url: str, item: dict) -> str:
        return self.detail_content


def test_pipeline_marks_shell_page_as_failed():
    result = run_detail_pipeline(
        title="微博热点",
        list_content="微博热点",
        strategy_results=[
            DetailStrategyResult(
                strategy="web_fallback",
                content="你访问的页面不见了 沪ICP备 营业执照",
            )
        ],
    )

    assert result.status == "failed"
    assert result.failure_reason == "shell_page"
    assert result.score == 0


def test_pipeline_marks_multi_source_content_as_complete():
    result = run_detail_pipeline(
        title="OpenAI 新发布会",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="topic_search",
                content="OpenAI 发布会上介绍了新模型、价格、开放计划。多位用户转发现场重点，并讨论开发者接入方式。",
            )
        ],
    )

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert result.score >= 80
    assert result.content_length >= 40


def test_pipeline_recognizes_relevant_mixed_keyword_content_as_complete():
    result = run_detail_pipeline(
        title="英伟达发布H200芯片",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="topic_search",
                content="H200芯片性能进一步提升，开发者开始讨论显存、训练效率和部署成本变化，产业侧也在评估新一代训练集群的升级节奏。",
            )
        ],
    )

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert result.failure_reason == ""


def test_safe_fetch_detail_preserves_long_complete_content():
    long_content = "OpenAI 发布新模型后，开发者重点关注 API 接入、推理成本和企业部署。" * 80
    crawler = LongContentCrawler(long_content)

    detail_content, status, error_message, pipeline = crawler.safe_fetch_detail(
        "https://example.com/openai-long-article",
        {"title": "OpenAI 发布新模型", "content": "列表摘要"},
    )

    assert status == "complete"
    assert error_message == ""
    assert detail_content == long_content
    assert pipeline.content_length == len(long_content)


def test_article_channel_requires_longer_content_than_hot_topic():
    short_context = (
        "OpenAI 发布新模型，开发者讨论 API 接入、推理成本、上下文管理和企业部署节奏。"
        "多位用户认为这会影响 Agent 应用、企业知识库和自动化测试流程。"
        "相关话题在微博热搜持续发酵，产品能力、开放时间和价格变化成为讨论焦点。"
        "但这些内容对技术文章来说仍然只是事件概述，还不是完整的方案正文。"
    )

    hot_result = run_detail_pipeline(
        title="OpenAI 发布新模型",
        list_content="列表摘要",
        strategy_results=[DetailStrategyResult(strategy="topic_search", content=short_context)],
        channel_code="weibo",
    )
    article_result = run_detail_pipeline(
        title="OpenAI 发布新模型",
        list_content="列表摘要",
        strategy_results=[DetailStrategyResult(strategy="fetch_detail", content=short_context)],
        channel_code="cnblogs",
    )

    assert hot_result.status == "complete"
    assert article_result.status == "partial"
    assert article_result.failure_reason == "content_below_channel_complete_threshold"
    assert article_result.score < hot_result.score


def test_finance_indicator_profile_accepts_explanatory_market_context():
    result = run_detail_pipeline(
        title="国际金价: 2350.20美元/盎司 ↑12.50",
        list_content="国际金价当前报2350.20美元/盎司。",
        strategy_results=[
            DetailStrategyResult(
                strategy="market_news_context",
                content=(
                    "国际金价当前报2350.20美元/盎司，较上一交易时段上涨12.50美元。"
                    "市场关注美元指数回落、避险需求升温和美联储政策预期变化，短期金价仍受通胀数据和地缘风险影响。"
                    "投资者同时观察美国就业数据、实际利率和央行购金节奏，若风险偏好继续下降，黄金走势可能保持偏强震荡。"
                    "机构认为，在政策预期没有明显转向前，市场会继续围绕避险需求和美元走势定价。"
                ),
            )
        ],
        channel_code="eastmoney",
    )

    assert result.status == "complete"
    assert result.score >= 80


def test_channel_detail_profile_defines_priority_channel_thresholds():
    assert get_channel_detail_profile("cnblogs").complete_min_length >= 500
    assert get_channel_detail_profile("reuters").complete_min_length >= 500
    assert get_channel_detail_profile("eastmoney").content_type == "finance_indicator"


def test_toutiao_profile_accepts_data_rich_event_context():
    result = run_detail_pipeline(
        title="假期第二天 全国路网维持高位运行",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="rendered_page",
                content=(
                    "假期第二天 全国路网维持高位运行。五一大假全国交通出行数据创历史同期新高，"
                    "全社会跨区域人员流动量预计达15.2亿人次，高速公路车流量日均约6400万辆次。"
                    "铁路、民航和公路部门发布实时运行情况，多地根据拥堵路段调整管控措施，"
                    "交通部门提醒游客错峰返程并关注天气、事故和服务区充电排队情况。"
                ),
            )
        ],
        channel_code="toutiao",
    )

    assert result.status == "complete"
    assert "low_channel_value_density" not in result.matched_rules


def test_toutiao_profile_accepts_compact_media_context():
    result = run_detail_pipeline(
        title="媒体：别让高价彩礼绊住婚姻幸福",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="rendered_page",
                content="媒体：别让高价彩礼绊住婚姻幸福。多地围绕彩礼、婚姻成本和移风易俗出台倡议，基层部门提醒理性消费。",
            )
        ],
        channel_code="toutiao",
    )

    assert result.status == "complete"
    assert result.score >= 80


def test_zhihu_profile_accepts_financial_analysis_context():
    result = run_detail_pipeline(
        title="五粮液 2026年Q1净利同比大增82.57%，如何解读？",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="search_embedded",
                content=(
                    "五粮液 2026年Q1净利同比大增82.57%，如何解读？报告期内，公司实现营业收入228.38亿元，"
                    "同比增长33.67%；归属于上市公司股东的净利润80.63亿元。分析人士认为，"
                    "高端白酒需求恢复、渠道库存改善和产品结构变化共同影响利润表现，投资者仍需关注现金流、"
                    "经销商回款、市场竞争以及后续季度增长能否延续。"
                ),
            )
        ],
        channel_code="zhihu",
    )

    assert result.status == "complete"
    assert "low_channel_value_density" not in result.matched_rules

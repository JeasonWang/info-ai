from services.detail_pipeline import DetailStrategyResult, run_detail_pipeline
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

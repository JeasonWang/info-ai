from tools.live_channel_quality_audit import audit_channels
from crawlers.registry import crawler_registry
from services.collection.detail_pipeline import DetailPipelineResult


class FakeCrawler:
    channel_code = "fake"
    channel_name = "测试渠道"

    def safe_crawl(self):
        return [
            {
                "title": "OpenAI 发布新模型",
                "content": "OpenAI 发布新模型",
                "source_url": "https://example.com/a",
            }
        ]

    def safe_fetch_detail(self, source_url, item):
        result = DetailPipelineResult(
            content="OpenAI 发布新模型，开发者正在讨论 API 接入、价格变化、企业部署和产品影响。",
            status="complete",
            strategy="fake_detail",
            score=88,
            content_length=45,
            failure_reason="",
            matched_rules=[],
        )
        return result.content, result.status, result.failure_reason, result


def test_live_channel_quality_audit_reports_sample_details():
    crawler_registry.register("fake", FakeCrawler())

    report = audit_channels(["fake"], limit=1)

    channel = report["channels"][0]
    assert channel["channel_code"] == "fake"
    assert channel["raw_count"] == 1
    assert channel["items"][0]["detail_status"] == "complete"
    assert channel["items"][0]["detail_strategy"] == "fake_detail"

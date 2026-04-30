from datetime import datetime

from crawlers.registry import crawler_registry
from database import Category, Channel, DetailJob, Info
from scheduler import _fetch_details_for_items, _save_crawled_data, process_detail_jobs
from services.detail_pipeline import DetailPipelineResult


def test_process_detail_jobs_enqueues_and_processes_low_quality_infos(session):
    category = Category(name="科技", code="tech", description="科技事件")
    session.add(category)
    session.flush()
    channel = Channel(name="36氪", code="36kr", base_url="https://36kr.com", category_id=category.id)
    session.add(channel)
    session.flush()
    info = Info(
        title="OpenAI 发布新模型",
        content="OpenAI 发布新模型",
        category_id=category.id,
        channel_id=channel.id,
        source_id="scheduler-detail-001",
        source_url="https://example.com/a",
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=8,
    )
    session.add(info)
    session.commit()

    def runner(item):
        return DetailPipelineResult(
            content="OpenAI 发布新模型，开发者关注推理能力、API 接入节奏和企业落地成本。",
            status="complete",
            strategy="scheduler_runner",
            score=90,
            content_length=36,
            failure_reason="",
            matched_rules=[],
        )

    result = process_detail_jobs(session=session, runner=runner, enqueue_limit=20, process_limit=20)

    assert result["enqueue"] == {"created_count": 1, "skipped_count": 0}
    assert result["process"] == {"succeeded_count": 1, "failed_count": 0}
    assert session.query(DetailJob).one().status == "succeeded"
    assert session.get(Info, info.id).detail_strategy == "scheduler_runner"


def test_save_crawled_data_marks_embedded_search_content_complete(session):
    category = Category(name="热点", code="hot", description="热点事件")
    session.add(category)
    session.flush()
    channel = Channel(name="知乎", code="zhihu", base_url="https://www.zhihu.com", category_id=category.id)
    session.add(channel)
    session.commit()

    saved_ids = _save_crawled_data(
        "zhihu",
        [
            {
                "source_id": "zhihu-search-embedded-001",
                "title": "微信朋友圈改版，你喜欢这个新样式吗？",
                "content": "微信朋友圈改版后，文字描述从配图右侧移至上方，并新增时间轴浏览功能。",
                "_search_content": "微信朋友圈改版后，文字描述从配图右侧移至上方，并新增时间轴浏览功能。腾讯客服回应称这是展示形式优化调整，用户可以继续反馈体验。",
                "source_url": "https://www.zhihu.com/question/2032722050247124724",
                "event_time": datetime.now(),
                "core_entity": "微信朋友圈改版",
                "location": "",
                "indicator_name": "hot_show",
                "indicator_value": "505 万",
            }
        ],
    )

    assert len(saved_ids) == 1
    info = session.get(Info, saved_ids[0])
    assert info.detail_fetch_status == "complete"
    assert info.detail_strategy == "search_embedded"
    assert info.detail_score >= 80
    assert "时间轴浏览功能" in info.content


def test_fetch_details_skips_already_complete_infos(session):
    category = Category(name="热点", code="hot", description="热点事件")
    session.add(category)
    session.flush()
    channel = Channel(name="知乎", code="zhihu", base_url="https://www.zhihu.com", category_id=category.id)
    session.add(channel)
    session.flush()
    info = Info(
        title="微信朋友圈改版，你喜欢这个新样式吗？",
        content="微信朋友圈改版后，文字描述从配图右侧移至上方，并新增时间轴浏览功能。腾讯客服回应称这是展示形式优化调整，用户可以继续反馈体验。",
        category_id=category.id,
        channel_id=channel.id,
        source_id="zhihu-complete-skip-001",
        source_url="https://www.zhihu.com/question/2032722050247124724",
        detail_fetch_status="complete",
        detail_strategy="search_embedded",
        detail_score=100,
        detail_content_length=65,
    )
    session.add(info)
    session.commit()

    class FailingCrawler:
        def safe_fetch_detail(self, source_url, item):
            raise AssertionError("complete records should not be fetched again")

    previous = crawler_registry.get("zhihu")
    crawler_registry.register("zhihu", FailingCrawler())
    try:
        result = _fetch_details_for_items("zhihu", [info.id])
    finally:
        if previous:
            crawler_registry.register("zhihu", previous)

    assert result == {"detail_success_count": 1, "detail_failed_count": 0}

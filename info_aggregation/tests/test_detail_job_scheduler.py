from datetime import datetime, timedelta

from crawlers.registry import crawler_registry
from database import Category, Channel, CrawlRunLog, CrawlTask, DetailJob, Event, EventAnalysisRun, EventItemLink, Info, InfoAcquisitionLog
from scheduler import _fetch_details_for_items, _save_crawled_data, crawl_by_category, process_detail_jobs
from services.collection.detail_pipeline import DetailPipelineResult


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


def test_process_detail_jobs_rebuilds_stale_event_analysis_after_detail_success(session):
    category = Category(name="AI", code="ai", description="AI")
    session.add(category)
    session.flush()
    channel = Channel(name="掘金", code="juejin", base_url="https://juejin.cn", category_id=category.id)
    session.add(channel)
    session.flush()
    info = Info(
        title="Agent 意图识别",
        content="短",
        category_id=category.id,
        channel_id=channel.id,
        source_id="scheduler-reanalysis-001",
        source_url="https://example.com/reanalysis",
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=2,
        core_entity="Agent",
    )
    event = Event(
        title="Agent 意图识别",
        one_line_summary="旧摘要",
        primary_category_id=category.id,
        status="active",
        source_count=1,
        last_updated_at=datetime.now(),
    )
    session.add_all([info, event])
    session.flush()
    session.add_all(
        [
            EventItemLink(event_id=event.id, item_id=info.id, role="primary", is_primary=1, weight=20),
            EventAnalysisRun(event_id=event.id, analysis_version="v1", mode="rule", provider="rule", status="succeeded"),
        ]
    )
    session.commit()

    def runner(item):
        return DetailPipelineResult(
            content="Agent 意图识别方案补齐了完整正文，解释了规则路由、大模型调用成本和复杂请求处理流程。",
            status="complete",
            strategy="scheduler_runner",
            score=92,
            content_length=40,
            failure_reason="",
            matched_rules=[],
        )

    result = process_detail_jobs(session=session, runner=runner, enqueue_limit=20, process_limit=20)

    assert result["reanalyze"]["rebuilt"] is True
    assert result["reanalyze"]["stale_count"] == 1
    assert session.query(EventAnalysisRun).filter(EventAnalysisRun.status == "stale").count() == 0
    assert session.query(EventAnalysisRun).filter(EventAnalysisRun.status == "succeeded").count() >= 1


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
                "title": "OpenAI 发布新模型，开发者如何评价？",
                "content": "OpenAI 发布新模型，开发者关注推理能力和 API 接入节奏。",
                "_search_content": (
                    "OpenAI 发布新模型，开发者关注推理能力、API 接入节奏和企业落地成本。"
                    "多位回答者讨论了上下文管理、工具调用、自动化测试以及发布流程中的注意事项。"
                    "从问答内容看，团队最关心的是新模型在复杂任务拆解、函数调用稳定性、长上下文记忆和企业权限治理上的表现。"
                    "也有回答补充了迁移成本、计费变化、监控告警和灰度发布策略，这些信息可以支撑后续事件分析。"
                    "还有观点认为，开发团队需要结合自身业务场景评估推理速度、上下文窗口、工具调用失败率和人工审核流程，"
                    "再决定是否把新模型用于生产环境的客服、代码生成、知识库检索和自动化运营任务。"
                ),
                "source_url": "https://www.zhihu.com/question/123456",
                "event_time": datetime.now(),
                "core_entity": "OpenAI",
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
    assert "API 接入节奏" in info.content
    assert session.query(InfoAcquisitionLog).filter(InfoAcquisitionLog.info_id == info.id).count() == 1
    assert info.tech_topic_type or info.tech_entities or info.tech_keywords


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


def test_crawl_by_category_only_runs_due_channel_tasks(session):
    category = Category(name="热点", code="hot", description="热点事件")
    session.add(category)
    session.flush()
    due_channel = Channel(
        name="到期渠道",
        code="due_channel",
        base_url="https://example.com/due",
        category_id=category.id,
        effective_interval_minutes=5,
    )
    future_channel = Channel(
        name="未到期渠道",
        code="future_channel",
        base_url="https://example.com/future",
        category_id=category.id,
        effective_interval_minutes=5,
    )
    session.add_all([due_channel, future_channel])
    session.flush()
    now = datetime.now()
    session.add_all(
        [
            CrawlTask(
                channel_id=due_channel.id,
                task_code="crawl_due_channel",
                task_name="到期渠道采集",
                schedule_type="interval",
                schedule_value="5",
                schedule_version=1,
                status="active",
                next_run_at=now - timedelta(minutes=1),
            ),
            CrawlTask(
                channel_id=future_channel.id,
                task_code="crawl_future_channel",
                task_name="未到期渠道采集",
                schedule_type="interval",
                schedule_value="5",
                schedule_version=1,
                status="active",
                next_run_at=now + timedelta(minutes=30),
            ),
        ]
    )
    session.commit()

    class CountingCrawler:
        def __init__(self, code):
            self.channel_code = code
            self.calls = 0

        def safe_crawl(self):
            self.calls += 1
            return []

    due_crawler = CountingCrawler("due_channel")
    future_crawler = CountingCrawler("future_channel")
    previous_due = crawler_registry.get("due_channel")
    previous_future = crawler_registry.get("future_channel")
    crawler_registry.register("due_channel", due_crawler)
    crawler_registry.register("future_channel", future_crawler)
    try:
        crawl_by_category("热点")
    finally:
        if previous_due:
            crawler_registry.register("due_channel", previous_due)
        if previous_future:
            crawler_registry.register("future_channel", previous_future)

    assert due_crawler.calls == 1
    assert future_crawler.calls == 0
    assert session.query(CrawlRunLog).filter(CrawlRunLog.channel_code == "due_channel").count() == 1
    assert session.query(CrawlRunLog).filter(CrawlRunLog.channel_code == "future_channel").count() == 0
    assert session.query(CrawlTask).filter(CrawlTask.task_code == "crawl_due_channel").one().next_run_at > now

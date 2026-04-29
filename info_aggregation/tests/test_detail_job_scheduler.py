from database import Category, Channel, DetailJob, Info
from scheduler import process_detail_jobs
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

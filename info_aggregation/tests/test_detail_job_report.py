from fastapi.testclient import TestClient

from api import app
from database import Category, Channel, DetailJob, Info
from services.detail_job_report import build_detail_job_report


def _seed_detail_job_report_data(session):
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
        source_id="detail-report-001",
        source_url="https://example.com/a",
        detail_fetch_status="list_only",
        detail_score=10,
        detail_content_length=8,
    )
    session.add(info)
    session.flush()
    session.add_all(
        [
            DetailJob(info_id=info.id, channel_code="36kr", status="pending", priority=80, last_failure_reason="low_detail_score"),
            DetailJob(info_id=info.id, channel_code="36kr", status="failed", priority=80, last_failure_reason="empty_content"),
        ]
    )
    session.commit()


def _seed_filterable_detail_job_report_data(session):
    category = Category(name="科技", code="tech", description="科技事件")
    session.add(category)
    session.flush()
    channels = [
        Channel(name="36氪", code="36kr", base_url="https://36kr.com", category_id=category.id),
        Channel(name="CSDN", code="csdn", base_url="https://csdn.net", category_id=category.id),
    ]
    session.add_all(channels)
    session.flush()
    for index, channel in enumerate(channels, start=1):
        info = Info(
            title=f"{channel.name} 详情样本",
            content="详情样本",
            category_id=category.id,
            channel_id=channel.id,
            source_id=f"detail-report-filter-{index}",
            source_url=f"https://example.com/{index}",
            detail_fetch_status="failed",
            detail_score=10,
            detail_content_length=4,
        )
        session.add(info)
        session.flush()
        session.add(
            DetailJob(
                info_id=info.id,
                channel_code=channel.code,
                status="failed",
                priority=80,
                last_failure_reason="empty_content" if channel.code == "36kr" else "blocked",
            )
        )
    session.commit()


def test_build_detail_job_report_counts_status_and_samples(session):
    _seed_detail_job_report_data(session)

    report = build_detail_job_report(session)

    assert report["total"] == 2
    assert report["status_counts"] == {"failed": 1, "pending": 1}
    assert report["channel_counts"] == {"36kr": 2}
    assert report["top_failure_reasons"] == [{"reason": "empty_content", "count": 1}, {"reason": "low_detail_score", "count": 1}]
    assert report["pending_samples"][0]["title"] == "OpenAI 发布新模型"


def test_build_detail_job_report_filters_by_channel_and_failure_reason(session):
    _seed_filterable_detail_job_report_data(session)

    report = build_detail_job_report(session, channel_code="36kr", failure_reason="empty_content")

    assert report["total"] == 1
    assert report["channel_counts"] == {"36kr": 1}
    assert report["top_failure_reasons"] == [{"reason": "empty_content", "count": 1}]
    assert report["failed_samples"][0]["channel_code"] == "36kr"


def test_admin_detail_jobs_api_returns_report(session):
    _seed_detail_job_report_data(session)
    client = TestClient(app)

    response = client.get("/api/admin/detail-jobs")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 2
    assert payload["status_counts"]["pending"] == 1


def test_admin_detail_jobs_api_accepts_filters(session):
    _seed_filterable_detail_job_report_data(session)
    client = TestClient(app)

    response = client.get("/api/admin/detail-jobs?channel_code=36kr&failure_reason=empty_content")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["channel_counts"] == {"36kr": 1}

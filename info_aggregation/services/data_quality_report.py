"""
数据质量体检报告。

这个模块只做可解释的统计，不直接修改数据。它用于 Plus 版本收尾阶段快速定位
“重复、空字段、详情残缺、事件摘要无效”等问题，帮助我们决定后续采集和清洗优先级。
"""
from collections import Counter

from database import DataQualitySnapshot, Event, Info
from services.data_quality import is_low_quality_list_item, is_title_content_duplicate, normalize_text, text_similarity


def _percent(count: int, total: int) -> float:
    """返回一位小数百分比，避免接口消费者重复计算。"""
    if total <= 0:
        return 0.0
    return round(count * 100 / total, 1)


def _is_missing_semantic(info: Info) -> bool:
    """判断科技语义字段是否完全缺失。"""
    return not any(
        [
            (info.tech_topic_type or "").strip(),
            (info.tech_entities or "").strip(),
            (info.tech_keywords or "").strip(),
        ]
    )


def _needs_semantic_fields(info: Info) -> bool:
    """只有科技和 AI 类内容强制要求语义字段，避免全站指标被非科技内容稀释。"""
    category = getattr(info, "category", None)
    category_text = f"{getattr(category, 'code', '')} {getattr(category, 'name', '')}".lower()
    return any(marker in category_text for marker in ["tech", "ai", "科技", "大模型"])


def _is_incomplete_detail(info: Info) -> bool:
    """判断详情采集是否仍然不足以支撑用户阅读。"""
    status = (info.detail_fetch_status or "").strip()
    if status in {"failed", "list_only", "pending"}:
        return True
    if status == "partial" and (info.detail_score or 0) < 60:
        return True
    return (info.detail_content_length or len(info.content or "")) < 30


def _is_seed_detail(info: Info) -> bool:
    """识别演示初始化数据，避免模拟完整详情污染真实采集质量口径。"""
    return (info.detail_strategy or "").strip().lower() == "seed"


def _is_real_complete_detail(info: Info) -> bool:
    """判断非 seed 数据是否已经具备可阅读的完整详情。"""
    if _is_seed_detail(info):
        return False
    return (
        (info.detail_fetch_status or "").strip() == "complete"
        and (info.detail_score or 0) >= 70
        and (info.detail_content_length or len(info.content or "")) >= 40
    )


def _count_duplicate_titles(infos: list[Info]) -> int:
    """统计归一化标题重复的内容条数，不包含每组第一条。"""
    counter = Counter(normalize_text(info.title) for info in infos if normalize_text(info.title))
    return sum(count - 1 for count in counter.values() if count > 1)


def _count_duplicate_source_urls(infos: list[Info]) -> int:
    """统计来源 URL 重复的内容条数，不包含每组第一条。"""
    counter = Counter(normalize_text(info.source_url) for info in infos if normalize_text(info.source_url))
    return sum(count - 1 for count in counter.values() if count > 1)


def _build_recommendations(metrics: dict) -> list[str]:
    """根据体检结果生成下一步治理建议。"""
    recommendations: list[str] = []

    if metrics["info"]["incomplete_detail_count"] > 0:
        recommendations.append("优先补强详情抓取，pending/list_only/failed 或短正文内容不应进入核心展示。")
    if metrics["info"]["missing_semantic_count"] > 0:
        recommendations.append("补强科技语义解析规则；无法稳定获取的实体和关键词不要强行展示给用户。")
    if metrics["info"]["duplicate_title_count"] > 0 or metrics["info"]["duplicate_source_url_count"] > 0:
        recommendations.append("加强入库去重，重复标题和重复来源 URL 应在采集保存阶段合并或跳过。")
    if metrics["event"]["title_summary_duplicate_count"] > 0:
        recommendations.append("重建事件摘要，避免 title 与 one_line_summary 表达同一件事。")
    if not recommendations:
        recommendations.append("当前核心质量指标健康，可以进入页面回归和真实采集压力测试。")

    return recommendations


def _info_sample(info: Info) -> dict:
    """输出最小问题样本，避免管理接口暴露大段正文。"""
    return {
        "id": info.id,
        "title": info.title,
        "source_id": info.source_id,
        "channel_name": info.channel.name if info.channel else "",
        "detail_fetch_status": info.detail_fetch_status,
        "detail_score": info.detail_score,
        "detail_content_length": info.detail_content_length or len(info.content or ""),
    }


def _build_issue_samples(infos: list[Info], semantic_infos: list[Info], limit: int = 5) -> dict:
    """列出最需要处理的问题样本，辅助下一轮采集器和解析规则优化。"""
    incomplete_details = [
        _info_sample(info)
        for info in sorted(
            [info for info in infos if _is_incomplete_detail(info)],
            key=lambda item: (item.detail_score or 0, item.detail_content_length or len(item.content or "")),
        )[:limit]
    ]
    missing_semantics = [
        _info_sample(info)
        for info in sorted(
            [info for info in semantic_infos if _is_missing_semantic(info)],
            key=lambda item: item.event_time or item.created_at,
            reverse=True,
        )[:limit]
    ]
    return {
        "incomplete_details": incomplete_details,
        "missing_semantics": missing_semantics,
    }


def build_data_quality_report(session) -> dict:
    """生成当前数据库的数据质量体检报告。"""
    infos = session.query(Info).filter(Info.is_deleted == 0).all()
    events = session.query(Event).all()

    low_quality_count = sum(1 for info in infos if is_low_quality_list_item(info.title, info.content))
    title_content_duplicate_count = sum(1 for info in infos if is_title_content_duplicate(info.title, info.content))
    incomplete_detail_count = sum(1 for info in infos if _is_incomplete_detail(info))
    seed_detail_count = sum(1 for info in infos if _is_seed_detail(info))
    real_detail_infos = [info for info in infos if not _is_seed_detail(info)]
    real_complete_detail_count = sum(1 for info in real_detail_infos if _is_real_complete_detail(info))
    semantic_infos = [info for info in infos if _needs_semantic_fields(info)]
    missing_semantic_count = sum(1 for info in semantic_infos if _is_missing_semantic(info))
    duplicate_title_count = _count_duplicate_titles(infos)
    duplicate_source_url_count = _count_duplicate_source_urls(infos)

    event_empty_summary_count = sum(1 for event in events if not (event.one_line_summary or "").strip())
    event_title_summary_duplicate_count = sum(
        1
        for event in events
        if event.one_line_summary
        and (
            is_title_content_duplicate(event.title, event.one_line_summary)
            or text_similarity(event.title, event.one_line_summary) >= 0.88
        )
    )

    metrics = {
        "info": {
            "total": len(infos),
            "low_quality_count": low_quality_count,
            "low_quality_ratio": _percent(low_quality_count, len(infos)),
            "title_content_duplicate_count": title_content_duplicate_count,
            "incomplete_detail_count": incomplete_detail_count,
            "incomplete_detail_ratio": _percent(incomplete_detail_count, len(infos)),
            "seed_detail_count": seed_detail_count,
            "real_detail_total": len(real_detail_infos),
            "real_complete_detail_count": real_complete_detail_count,
            "real_complete_detail_ratio": _percent(real_complete_detail_count, len(real_detail_infos)),
            "semantic_scope_total": len(semantic_infos),
            "missing_semantic_count": missing_semantic_count,
            "missing_semantic_ratio": _percent(missing_semantic_count, len(semantic_infos)),
            "duplicate_title_count": duplicate_title_count,
            "duplicate_source_url_count": duplicate_source_url_count,
        },
        "event": {
            "total": len(events),
            "empty_summary_count": event_empty_summary_count,
            "title_summary_duplicate_count": event_title_summary_duplicate_count,
            "title_summary_duplicate_ratio": _percent(event_title_summary_duplicate_count, len(events)),
        },
    }
    return {
        **metrics,
        "samples": _build_issue_samples(infos, semantic_infos),
        "recommendations": _build_recommendations(metrics),
    }


def save_data_quality_snapshot(session, category_code: str = "all") -> DataQualitySnapshot:
    """把当前质量体检结果保存到 Pro 监控快照表。"""
    report = build_data_quality_report(session)
    info_metrics = report["info"]
    snapshot = DataQualitySnapshot(
        category_code=category_code,
        total_count=info_metrics["total"],
        duplicate_title_count=info_metrics["duplicate_title_count"],
        empty_content_count=sum(
            1
            for info in session.query(Info).filter(Info.is_deleted == 0).all()
            if not (info.content or "").strip()
        ),
        low_detail_score_count=sum(
            1
            for info in session.query(Info).filter(Info.is_deleted == 0).all()
            if (info.detail_score or 0) < 60
        ),
        missing_entity_count=info_metrics["missing_semantic_count"],
        snapshot_payload=report,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot

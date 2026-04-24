"""
信息聚合系统 - FastAPI接口模块
提供信息查询、分类查询、渠道查询等RESTful API
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import or_

from database import (
    get_session,
    Category,
    Channel,
    Event,
    EventItemLink,
    EventSummarySnapshot,
    EventTimelineEntry,
    Info,
)
from services import (
	archive_duplicate_title_infos,
	archive_low_quality_infos,
	build_data_quality_report,
	rebuild_events,
	refresh_info_semantics,
)
from services.data_quality import text_similarity
from services.data_quality_report import save_data_quality_snapshot

logger = logging.getLogger(__name__)


def _split_csv(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _build_event_tech_context(source_rows) -> dict:
    """
    从事件关联的原始内容里聚合科技上下文，供事件详情页直接消费。
    """
    topic_counter: dict[str, int] = {}
    entity_counter: dict[str, int] = {}
    keyword_counter: dict[str, int] = {}

    for _, info, _ in source_rows:
        if info.tech_topic_type:
            topic_counter[info.tech_topic_type] = topic_counter.get(info.tech_topic_type, 0) + 1
        for entity in _split_csv(info.tech_entities):
            entity_counter[entity] = entity_counter.get(entity, 0) + 1
        for keyword in _split_csv(info.tech_keywords):
            keyword_counter[keyword] = keyword_counter.get(keyword, 0) + 1

    top_topics = [
        {"topic_type": topic_type, "count": count}
        for topic_type, count in sorted(topic_counter.items(), key=lambda item: (-item[1], item[0]))[:3]
    ]
    entities = [
        entity
        for entity, _ in sorted(entity_counter.items(), key=lambda item: (-item[1], item[0]))[:6]
    ]
    keywords = [
        keyword
        for keyword, _ in sorted(keyword_counter.items(), key=lambda item: (-item[1], item[0]))[:8]
    ]

    return {
        "topics": top_topics,
        "entities": entities,
        "keywords": keywords,
    }


def _is_redundant_text(text: str, existing_texts: list[str], threshold: float = 0.9) -> bool:
    cleaned = " ".join((text or "").split()).strip()
    if not cleaned:
        return True
    for existing in existing_texts:
        existing_cleaned = " ".join((existing or "").split()).strip()
        if not existing_cleaned:
            continue
        if cleaned in existing_cleaned or existing_cleaned in cleaned:
            return True
        if text_similarity(cleaned, existing_cleaned) >= threshold:
            return True
    return False


def _build_distinct_source_views(source_rows, summaries: dict) -> list[dict]:
    views = []
    seen_channels = set()
    reference_texts = [value for value in summaries.values() if value]

    for _, info, channel in source_rows:
        summary = " ".join((info.content or "")[:120].split()).strip()
        if not summary or channel.name in seen_channels:
            continue
        if _is_redundant_text(summary, reference_texts, threshold=0.86):
            continue
        views.append({"channel_name": channel.name, "summary": summary})
        seen_channels.add(channel.name)
        reference_texts.append(summary)
        if len(views) >= 3:
            break

    return views


class CategoryPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=50)
    description: str = Field(default="", max_length=200)


class ChannelPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=50)
    base_url: str = Field(default="", max_length=255)
    category_id: int
    crawl_interval: int = Field(default=60, ge=1)
    is_active: int = Field(default=1, ge=0, le=1)

app = FastAPI(
    title="信息聚合系统 API",
    description="多渠道信息聚合系统，提供热点事件、经济数据、国际大事、科技动向、AI大模型动向等信息查询",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """系统根路径，返回系统信息"""
    return {
        "system": "信息聚合系统",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.get("/api/categories")
def list_categories():
    """
    获取所有信息分类
    返回: 分类列表
    """
    session = get_session()
    try:
        categories = session.query(Category).all()
        return {
            "code": 0,
            "message": "success",
            "data": [c.to_dict() for c in categories],
        }
    finally:
        session.close()


@app.get("/api/event-categories")
def list_event_categories():
    return {
        "code": 0,
        "message": "success",
        "data": [
            {"code": "all", "name": "全网", "display_order": 0},
            {"code": "tech", "name": "科技", "display_order": 1},
            {"code": "economy", "name": "财经", "display_order": 2},
            {"code": "sports", "name": "体育", "display_order": 3},
            {"code": "international", "name": "国际", "display_order": 4},
        ],
    }


@app.get("/api/channels")
def list_channels(
    category_id: Optional[int] = Query(None, description="按分类ID筛选"),
    include_inactive: bool = Query(False, description="是否包含停用渠道"),
):
    """
    获取渠道列表
    参数:
        category_id: 可选，按分类ID筛选
    返回: 渠道列表
    """
    session = get_session()
    try:
        query = session.query(Channel)
        if category_id:
            query = query.filter(Channel.category_id == category_id)
        if not include_inactive:
            query = query.filter(Channel.is_active == 1)
        channels = query.order_by(Channel.id.asc()).all()
        return {
            "code": 0,
            "message": "success",
            "data": [ch.to_dict() for ch in channels],
        }
    finally:
        session.close()


@app.get("/api/admin/categories")
def admin_list_categories():
    session = get_session()
    try:
        categories = session.query(Category).order_by(Category.id.asc()).all()
        return {
            "code": 0,
            "message": "success",
            "data": [item.to_dict() for item in categories],
        }
    finally:
        session.close()


@app.post("/api/admin/categories")
def admin_create_category(payload: CategoryPayload):
    session = get_session()
    try:
        if session.query(Category).filter(Category.name == payload.name).first():
            raise HTTPException(status_code=400, detail="分类名称已存在")
        if session.query(Category).filter(Category.code == payload.code).first():
            raise HTTPException(status_code=400, detail="分类编码已存在")

        category = Category(
            name=payload.name.strip(),
            code=payload.code.strip(),
            description=payload.description.strip(),
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return {
            "code": 0,
            "message": "success",
            "data": category.to_dict(),
        }
    finally:
        session.close()


@app.put("/api/admin/categories/{category_id}")
def admin_update_category(category_id: int, payload: CategoryPayload):
    session = get_session()
    try:
        category = session.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

        if session.query(Category).filter(Category.name == payload.name, Category.id != category_id).first():
            raise HTTPException(status_code=400, detail="分类名称已存在")
        if session.query(Category).filter(Category.code == payload.code, Category.id != category_id).first():
            raise HTTPException(status_code=400, detail="分类编码已存在")

        category.name = payload.name.strip()
        category.code = payload.code.strip()
        category.description = payload.description.strip()
        session.commit()
        session.refresh(category)
        return {
            "code": 0,
            "message": "success",
            "data": category.to_dict(),
        }
    finally:
        session.close()


@app.get("/api/admin/channels")
def admin_list_channels():
    session = get_session()
    try:
        channels = session.query(Channel).order_by(Channel.id.asc()).all()
        return {
            "code": 0,
            "message": "success",
            "data": [item.to_dict() for item in channels],
        }
    finally:
        session.close()


@app.post("/api/admin/channels")
def admin_create_channel(payload: ChannelPayload):
    session = get_session()
    try:
        if not session.query(Category).filter(Category.id == payload.category_id).first():
            raise HTTPException(status_code=400, detail="分类不存在")
        if session.query(Channel).filter(Channel.name == payload.name).first():
            raise HTTPException(status_code=400, detail="渠道名称已存在")
        if session.query(Channel).filter(Channel.code == payload.code).first():
            raise HTTPException(status_code=400, detail="渠道编码已存在")

        channel = Channel(
            name=payload.name.strip(),
            code=payload.code.strip(),
            base_url=payload.base_url.strip(),
            category_id=payload.category_id,
            crawl_interval=payload.crawl_interval,
            is_active=payload.is_active,
        )
        session.add(channel)
        session.commit()
        session.refresh(channel)
        return {
            "code": 0,
            "message": "success",
            "data": channel.to_dict(),
        }
    finally:
        session.close()


@app.put("/api/admin/channels/{channel_id}")
def admin_update_channel(channel_id: int, payload: ChannelPayload):
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="渠道不存在")
        if not session.query(Category).filter(Category.id == payload.category_id).first():
            raise HTTPException(status_code=400, detail="分类不存在")
        if session.query(Channel).filter(Channel.name == payload.name, Channel.id != channel_id).first():
            raise HTTPException(status_code=400, detail="渠道名称已存在")
        if session.query(Channel).filter(Channel.code == payload.code, Channel.id != channel_id).first():
            raise HTTPException(status_code=400, detail="渠道编码已存在")

        channel.name = payload.name.strip()
        channel.code = payload.code.strip()
        channel.base_url = payload.base_url.strip()
        channel.category_id = payload.category_id
        channel.crawl_interval = payload.crawl_interval
        channel.is_active = payload.is_active
        session.commit()
        session.refresh(channel)
        return {
            "code": 0,
            "message": "success",
            "data": channel.to_dict(),
        }
    finally:
        session.close()


@app.get("/api/infos")
def list_infos(
    category_id: Optional[int] = Query(None, description="按分类ID筛选"),
    channel_id: Optional[int] = Query(None, description="按渠道ID筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    分页查询信息列表
    参数:
        category_id: 可选，按分类ID筛选
        channel_id: 可选，按渠道ID筛选
        keyword: 可选，关键词搜索（标题/内容）
        page: 页码，默认1
        page_size: 每页数量，默认20
    返回: 分页信息列表
    """
    session = get_session()
    try:
        query = session.query(Info).filter(Info.is_deleted == 0)

        if category_id:
            query = query.filter(Info.category_id == category_id)
        if channel_id:
            query = query.filter(Info.channel_id == channel_id)
        if keyword:
            query = query.filter(
                (Info.title.contains(keyword)) | (Info.content.contains(keyword))
            )

        total = query.count()
        items = query.order_by(Info.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "code": 0,
            "message": "success",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [item.to_dict() for item in items],
            },
        }
    finally:
        session.close()


@app.get("/api/events")
def list_events(
    category_code: str = Query("all", description="按分类编码筛选"),
    keyword: Optional[str] = Query(None, description="按关键词筛选事件"),
    sort: str = Query("composite", description="排序方式: composite-综合分 latest-最新更新"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
):
    session = get_session()
    try:
        query = session.query(Event)
        if category_code != "all":
            query = query.join(Category, Category.id == Event.primary_category_id).filter(Category.code == category_code)
        if keyword:
            query = query.filter(
                or_(
                    Event.title.contains(keyword),
                    Event.one_line_summary.contains(keyword),
                )
            )

        total = query.count()
        if sort == "latest":
            query = query.order_by(Event.last_updated_at.desc(), Event.composite_score.desc())
        else:
            query = query.order_by(Event.composite_score.desc(), Event.last_updated_at.desc())

        items = query.offset((page - 1) * page_size).limit(page_size).all()

        def build_badges(event_id: int) -> list[str]:
            rows = (
                session.query(Channel.name)
                .join(Info, Info.channel_id == Channel.id)
                .join(EventItemLink, EventItemLink.item_id == Info.id)
                .filter(EventItemLink.event_id == event_id)
                .limit(3)
                .all()
            )
            badges = []
            seen = set()
            for (name,) in rows:
                if name in seen:
                    continue
                badges.append(name)
                seen.add(name)
            return badges

        def get_representative_info_id(event_id: int) -> Optional[int]:
            row = (
                session.query(EventItemLink.item_id)
                .filter(EventItemLink.event_id == event_id)
                .order_by(EventItemLink.is_primary.desc(), EventItemLink.weight.desc(), EventItemLink.id.asc())
                .first()
            )
            return row[0] if row else None

        return {
            "code": 0,
            "message": "success",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [
                    {
                        "id": item.id,
                        "representative_info_id": get_representative_info_id(item.id),
                        "title": item.title,
                        "one_line_summary": item.one_line_summary,
                        "primary_category": {"code": item.category.code, "name": item.category.name},
                        "heat_score": item.heat_score,
                        "freshness_score": item.freshness_score,
                        "composite_score": item.composite_score,
                        "last_updated_at": item.last_updated_at.strftime("%Y-%m-%d %H:%M:%S") if item.last_updated_at else None,
                        "source_count": item.source_count,
                        "source_badges": build_badges(item.id),
                        "new_update_count": max(0, item.source_count - 1),
                    }
                    for item in items
                ],
            },
        }
    finally:
        session.close()


@app.get("/api/infos/{info_id}")
def get_info(info_id: int):
    """
    获取单条信息详情
    参数:
        info_id: 信息ID
    返回: 信息详情
    """
    session = get_session()
    try:
        info = session.query(Info).filter(Info.id == info_id, Info.is_deleted == 0).first()
        if not info:
            raise HTTPException(status_code=404, detail="信息不存在")
        return {
            "code": 0,
            "message": "success",
            "data": info.to_dict(),
        }
    finally:
        session.close()


@app.get("/api/events/{event_id}")
def get_event_detail(event_id: int):
    session = get_session()
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="事件不存在")

        summaries = {
            item.summary_type: item.content
            for item in session.query(EventSummarySnapshot).filter(EventSummarySnapshot.event_id == event_id).all()
        }
        raw_timeline = (
            session.query(EventTimelineEntry)
            .filter(EventTimelineEntry.event_id == event_id)
            .order_by(EventTimelineEntry.occurred_at.asc())
            .all()
        )
        timeline = []
        seen_timeline_summaries: list[str] = [value for value in summaries.values() if value]
        for item in raw_timeline:
            if _is_redundant_text(item.summary, seen_timeline_summaries):
                continue
            timeline.append(item)
            seen_timeline_summaries.append(item.summary)
        source_rows = (
            session.query(EventItemLink, Info, Channel)
            .join(Info, Info.id == EventItemLink.item_id)
            .join(Channel, Channel.id == Info.channel_id)
            .filter(EventItemLink.event_id == event_id)
            .order_by(EventItemLink.weight.desc())
            .all()
        )
        tech_context = _build_event_tech_context(source_rows)

        return {
            "code": 0,
            "message": "success",
            "data": {
                "event": {
                    "id": event.id,
                    "title": event.title,
                    "one_line_summary": event.one_line_summary,
                    "primary_category": {"code": event.category.code, "name": event.category.name},
                    "heat_score": event.heat_score,
                    "freshness_score": event.freshness_score,
                    "composite_score": event.composite_score,
                    "source_count": event.source_count,
                    "last_updated_at": event.last_updated_at.strftime("%Y-%m-%d %H:%M:%S") if event.last_updated_at else None,
                },
                "timeline": [
                    {
                        "id": item.id,
                        "occurred_at": item.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "summary": item.summary,
                        "confidence": item.confidence,
                    }
                    for item in timeline
                ],
                "summaries": summaries,
                "source_views": _build_distinct_source_views(source_rows, summaries),
                "representative_sources": [
                    {
                        "info_id": info.id,
                        "title": info.title,
                        "channel_name": channel.name,
                        "source_url": info.source_url,
                        "event_time": info.event_time.strftime("%Y-%m-%d %H:%M:%S") if info.event_time else None,
                    }
                    for _, info, channel in source_rows[:6]
                ],
                "tech_context": tech_context,
            },
        }
    finally:
        session.close()


@app.get("/api/stats")
def get_stats():
    """
    获取系统统计信息
    返回: 各分类信息数量统计
    """
    session = get_session()
    try:
        from sqlalchemy import func
        stats = (
            session.query(
                Category.name,
                func.count(Info.id).label("count"),
            )
            .outerjoin(Info, Info.category_id == Category.id)
            .filter(Info.is_deleted == 0)
            .group_by(Category.id)
            .all()
        )
        total = session.query(Info).filter(Info.is_deleted == 0).count()
        return {
            "code": 0,
            "message": "success",
            "data": {
                "total": total,
                "categories": [
                    {"name": name, "count": count}
                    for name, count in stats
                ],
            },
        }
    finally:
        session.close()


@app.post("/api/admin/rebuild-events")
def admin_rebuild_events():
    session = get_session()
    try:
        rebuild_events(session)
        event_count = session.query(Event).count()
        return {
            "code": 0,
            "message": "success",
            "data": {"event_count": event_count},
        }
    finally:
        session.close()


@app.post("/api/admin/refresh-quality")
def admin_refresh_quality():
    session = get_session()
    try:
        semantic_result = refresh_info_semantics(session)
        rebuild_events(session)
        event_count = session.query(Event).count()
        return {
            "code": 0,
            "message": "success",
            "data": {
                **semantic_result,
                "event_count": event_count,
            },
        }
    finally:
        session.close()


@app.post("/api/admin/retry-low-quality-details")
def admin_retry_low_quality_details(limit: int = Query(20, ge=1, le=50, description="本次最多重抓的低完整内容数量")):
    """按渠道重抓低完整详情，解决详情页正文缺失或质量分偏低的问题。"""
    from scheduler import _fetch_details_for_items

    session = get_session()
    try:
        infos = (
            session.query(Info)
            .join(Channel, Channel.id == Info.channel_id)
            .filter(Info.is_deleted == 0)
            .filter(
                (Info.detail_fetch_status != "complete")
                | (Info.detail_score < 80)
                | (Info.detail_content_length < 120)
                | (Info.content == None)
                | (Info.content == "")
            )
            .order_by(Info.detail_score.asc(), Info.detail_content_length.asc(), Info.updated_at.desc())
            .limit(limit)
            .all()
        )
        grouped_ids = {}
        for info in infos:
            channel_code = info.channel.code if info.channel else ""
            if not channel_code:
                continue
            grouped_ids.setdefault(channel_code, []).append(info.id)
    finally:
        session.close()

    total_success = 0
    total_failed = 0
    channel_results = {}
    for channel_code, ids in grouped_ids.items():
        result = _fetch_details_for_items(channel_code, ids)
        success_count = int(result.get("detail_success_count", 0))
        failed_count = int(result.get("detail_failed_count", 0))
        total_success += success_count
        total_failed += failed_count
        channel_results[channel_code] = {
            "info_ids": ids,
            "detail_success_count": success_count,
            "detail_failed_count": failed_count,
        }

    session = get_session()
    try:
        semantic_result = refresh_info_semantics(session)
        rebuild_events(session)
        snapshot = save_data_quality_snapshot(session)
        event_count = session.query(Event).count()
        return {
            "code": 0,
            "message": "success",
            "data": {
                "selected_count": len(infos),
                "detail_success_count": total_success,
                "detail_failed_count": total_failed,
                "channel_results": channel_results,
                "semantic_updated_count": semantic_result.get("updated_count", 0),
                "quality_snapshot_id": snapshot.id,
                "event_count": event_count,
            },
        }
    finally:
        session.close()


@app.get("/api/admin/data-quality-report")
def admin_data_quality_report():
    """返回数据库质量体检结果，供 Plus 版本收尾和后续采集治理使用。"""
    session = get_session()
    try:
        return {
            "code": 0,
            "message": "success",
            "data": build_data_quality_report(session),
        }
    finally:
        session.close()


@app.post("/api/admin/archive-low-quality")
def admin_archive_low_quality():
    """软删除明显低质量内容，并重建事件流。"""
    session = get_session()
    try:
        archive_result = archive_low_quality_infos(session)
        rebuild_events(session)
        return {
            "code": 0,
            "message": "success",
            "data": {
                **archive_result,
                "event_count": session.query(Event).count(),
                "quality_report": build_data_quality_report(session),
            },
        }
    finally:
        session.close()


@app.post("/api/admin/archive-duplicate-titles")
def admin_archive_duplicate_titles():
    """软删除重复标题内容，每组保留质量最高的一条，并重建事件流。"""
    session = get_session()
    try:
        archive_result = archive_duplicate_title_infos(session)
        rebuild_events(session)
        return {
            "code": 0,
            "message": "success",
            "data": {
                **archive_result,
                "event_count": session.query(Event).count(),
                "quality_report": build_data_quality_report(session),
            },
        }
    finally:
        session.close()


@app.post("/api/crawl/trigger")
def trigger_crawl(channel_code: str = Query(..., description="渠道编码")):
    """
    手动触发指定渠道的爬取任务
    参数:
        channel_code: 渠道编码
    返回: 爬取结果
    """
    from crawlers.registry import crawler_registry
    from cleaners import clean_info_list

    crawler = crawler_registry.get(channel_code)
    if not crawler:
        raise HTTPException(status_code=404, detail=f"渠道 {channel_code} 未注册")

    raw_items = crawler.safe_crawl()
    cleaned_items = clean_info_list(raw_items)

    from scheduler import _save_crawled_data, _fetch_details_for_items

    saved_ids = _save_crawled_data(channel_code, cleaned_items)
    _fetch_details_for_items(channel_code, saved_ids)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "channel": channel_code,
            "raw_count": len(raw_items),
            "cleaned_count": len(cleaned_items),
            "detail_fetched": len(saved_ids),
        },
    }

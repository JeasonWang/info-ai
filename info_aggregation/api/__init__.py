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
from services import rebuild_events

logger = logging.getLogger(__name__)


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
        items = (
            query.order_by(Event.composite_score.desc(), Event.last_updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        def build_badges(event_id: int) -> list[str]:
            rows = (
                session.query(Channel.name)
                .join(Info, Info.channel_id == Channel.id)
                .join(EventItemLink, EventItemLink.item_id == Info.id)
                .filter(EventItemLink.event_id == event_id)
                .limit(3)
                .all()
            )
            return [name for (name,) in rows]

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
        timeline = (
            session.query(EventTimelineEntry)
            .filter(EventTimelineEntry.event_id == event_id)
            .order_by(EventTimelineEntry.occurred_at.asc())
            .all()
        )
        source_rows = (
            session.query(EventItemLink, Info, Channel)
            .join(Info, Info.id == EventItemLink.item_id)
            .join(Channel, Channel.id == Info.channel_id)
            .filter(EventItemLink.event_id == event_id)
            .order_by(EventItemLink.weight.desc())
            .all()
        )

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
                "source_views": [
                    {"channel_name": channel.name, "summary": info.content[:120]}
                    for _, info, channel in source_rows[:3]
                ],
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

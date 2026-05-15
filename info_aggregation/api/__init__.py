"""
信息聚合系统 - FastAPI健康检查模块。

业务读写接口由 info-serve 承担；采集和分析动作通过 Redis 命令总线触发。
旧 `/api/*` 接口仅在 ENABLE_PUBLIC_API=1 时作为测试兼容入口挂载。
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import or_, text

from config import CORS_ALLOWED_ORIGINS, ENABLE_PUBLIC_API
from database import (
    get_session,
    Category,
    Channel,
    Event,
    EventAnalysisRun,
    EventAnalysisSource,
    EventItemLink,
    EventSummarySnapshot,
    EventTimelineEntry,
    Info,
    DetailJob,
)
from services import (
	archive_duplicate_title_infos,
	archive_low_quality_infos,
	build_channel_quality_report,
	build_credential_report,
	build_data_quality_report,
	build_event_analysis_quality_report,
    enqueue_event_analysis_detail_jobs,
    mark_low_confidence_complete_events_stale,
    prioritize_source_quality_governance,
    rebuild_stale_event_analysis,
	create_llm_model_config,
	list_llm_model_configs,
	rebuild_events,
	refresh_info_semantics,
	update_llm_model_config,
)
from services.quality.data_quality import text_similarity
from services.quality.data_quality_report import save_data_quality_snapshot
from services.quality.detail_job_report import build_detail_job_report
from services.collection.acquisition_quality import build_acquisition_quality_profile, quality_profile_to_dict
from services.llm import run_llm_chat_completion, run_llm_chat_test

logger = logging.getLogger(__name__)


def _info_with_quality(info: Info) -> dict:
    data = info.to_dict()
    data["acquisition_quality"] = quality_profile_to_dict(build_acquisition_quality_profile(info))
    return data


def _run_manual_crawl(channel_code: str):
    """后台执行手动采集，避免管理后台 HTTP 请求被慢渠道阻塞。"""
    from crawlers.registry import crawler_registry
    from cleaners import clean_info_list
    from scheduler import (
        _fetch_details_for_items,
        _record_crawl_run,
        _save_crawled_data,
        _sync_crawl_tasks,
    )

    started_at = datetime.now()
    raw_count = 0
    cleaned_count = 0
    saved_count = 0
    detail_result = {"detail_success_count": 0, "detail_failed_count": 0}
    status = "success"
    error_message = ""

    try:
        crawler = crawler_registry.get(channel_code)
        if not crawler:
            status = "failed"
            error_message = f"渠道 {channel_code} 未注册"
            return

        with crawler_registry.get_lock(channel_code):
            raw_items = crawler.safe_crawl()
        raw_count = len(raw_items)
        cleaned_items = clean_info_list(raw_items)
        cleaned_count = len(cleaned_items)
        saved_ids = _save_crawled_data(channel_code, cleaned_items)
        saved_count = len(saved_ids)
        detail_result = _fetch_details_for_items(channel_code, saved_ids)
        if detail_result["detail_failed_count"] > 0:
            status = "partial"
    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        logger.error(f"渠道 {channel_code} 手动采集失败: {exc}", exc_info=True)
    finally:
        session = get_session()
        try:
            _sync_crawl_tasks(session)
            _record_crawl_run(
                session,
                channel_code=channel_code,
                trigger_type="manual",
                status=status,
                raw_count=raw_count,
                cleaned_count=cleaned_count,
                saved_count=saved_count,
                detail_success_count=detail_result["detail_success_count"],
                detail_failed_count=detail_result["detail_failed_count"],
                error_message=error_message,
                started_at=started_at,
                finished_at=datetime.now(),
            )
            rebuild_events(session)
            save_data_quality_snapshot(session)
        finally:
            session.close()


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


def _source_quality(info: Info) -> dict:
    profile = build_acquisition_quality_profile(info)
    return {
        "quality_level": profile.quality_level,
        "usable": profile.usable,
        "needs_attention": profile.needs_attention,
        "completeness_score": profile.completeness_score,
        "value_score": profile.value_score,
        "risk_reasons": profile.risk_reasons,
        "summary": profile.summary,
    }


def _is_evidence_source(quality: dict) -> bool:
    if quality["usable"]:
        return True
    risk_reasons = set(quality["risk_reasons"])
    hard_risks = {"anti_crawl_or_shell_page", "empty_content", "title_only_content", "seed_data"}
    return quality["quality_level"] == "weak" and not risk_reasons.intersection(hard_risks)


def _build_event_evidence_chain(source_rows) -> dict:
    evidence_sources = []
    weak_sources = []
    platform_counter: dict[str, int] = {}

    for link, info, channel in source_rows:
        quality = _source_quality(info)
        platform_counter[channel.name] = platform_counter.get(channel.name, 0) + 1
        source = {
            "info_id": info.id,
            "title": info.title,
            "channel_name": channel.name,
            "source_url": info.source_url,
            "weight": link.weight,
            "detail_score": info.detail_score or 0,
            "detail_fetch_status": info.detail_fetch_status or "",
            "quality_level": quality["quality_level"],
            "quality_summary": quality["summary"],
            "risk_reasons": quality["risk_reasons"],
        }
        if _is_evidence_source(quality):
            evidence_sources.append(source)
        else:
            weak_sources.append(source)

    platform_views = [
        {"channel_name": name, "source_count": count}
        for name, count in sorted(platform_counter.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        "evidence_sources": evidence_sources[:5],
        "weak_sources": weak_sources[:5],
        "platform_views": platform_views,
        "usable_source_count": len(evidence_sources),
        "weak_source_count": len(weak_sources),
    }


class CategoryPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=50)
    description: str = Field(default="", max_length=200)


class ChannelPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=50)
    base_url: str = Field(default="", max_length=255)
    category_id: int
    crawl_interval: int = Field(default=60, ge=1)  # 已废弃，保留兼容
    base_interval_minutes: int = Field(default=60, ge=1)
    hot_interval_minutes: int = Field(default=10, ge=1)
    min_interval_minutes: int = Field(default=3, ge=1)
    max_interval_minutes: int = Field(default=240, ge=1)
    manual_interval_enabled: int = Field(default=1, ge=0, le=1)
    effective_interval_minutes: int = Field(default=60, ge=1)
    is_active: int = Field(default=1, ge=0, le=1)


class ChannelCredentialPayload(BaseModel):
    """渠道凭证更新请求。"""
    cookies: str = Field(default="", description="Cookie字符串或JSON格式")
    extra_credentials: dict = Field(default=None, description="扩展凭证，如 {\"zhihu\": {\"zse_93\": \"...\", \"zse_96\": \"...\"}}")
    updated_by: str = Field(default="admin", max_length=100, description="更新操作人")


class LLMModelConfigPayload(BaseModel):
    provider_name: str = Field(..., min_length=1, max_length=50)
    provider_code: str = Field(..., min_length=1, max_length=50)
    base_url: str = Field(default="", max_length=255)
    api_key: str = Field(default="", max_length=500)
    model_name: str = Field(..., min_length=1, max_length=100)
    is_enabled: int = Field(default=0, ge=0, le=1)
    daily_call_limit: int = Field(default=0, ge=0)
    daily_call_count: int = Field(default=0, ge=0)
    priority: int = Field(default=100, ge=1)


class LLMChatTestPayload(BaseModel):
    config_id: Optional[int] = Field(default=None, ge=1)
    prompt: str = Field(default="请返回JSON：{\"ok\":true,\"summary\":\"大模型连接正常\"}", min_length=1, max_length=4000)
    timeout_seconds: int = Field(default=180, ge=10, le=600)


class LLMChatPayload(BaseModel):
    config_id: Optional[int] = Field(default=None, ge=1)
    message: str = Field(..., min_length=1, max_length=8000)
    timeout_seconds: int = Field(default=240, ge=10, le=600)


def _apply_channel_schedule_config(channel: Channel, payload: ChannelPayload):
    """同步管理后台提交的采集间隔配置，并推进调度版本供 worker 热更新。"""
    previous_version = channel.schedule_version or 0
    channel.base_interval_minutes = payload.base_interval_minutes
    channel.hot_interval_minutes = payload.hot_interval_minutes
    channel.min_interval_minutes = payload.min_interval_minutes
    channel.max_interval_minutes = payload.max_interval_minutes
    channel.manual_interval_enabled = payload.manual_interval_enabled
    channel.effective_interval_minutes = payload.effective_interval_minutes
    channel.schedule_version = previous_version + 1

app = FastAPI(
    title="信息聚合系统 API",
    description="多渠道信息聚合系统，提供热点事件、经济数据、国际大事、科技动向、AI大模型动向等信息查询",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """API 启动时初始化需要数据库会话的全局组件。"""
    from services.collection.credential_provider import CredentialProvider

    CredentialProvider.get_instance(session_factory=get_session)


@app.get("/")
def root():
    """系统根路径，返回系统信息"""
    return {
        "system": "信息聚合系统",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.get("/health")
def health():
    return {
        "code": 0,
        "message": "success",
        "data": {
            "service": "info_aggregation",
            "status": "healthy",
            "public_api_enabled": ENABLE_PUBLIC_API,
        },
    }


@app.get("/ready")
def ready():
    session = get_session()
    try:
        session.execute(text("SELECT 1"))
        return {
            "code": 0,
            "message": "success",
            "data": {
                "service": "info_aggregation",
                "status": "ready",
                "public_api_enabled": ENABLE_PUBLIC_API,
            },
        }
    finally:
        session.close()


def public_api_route(method: str, path: str):
    """仅在测试/过渡期开启旧业务 HTTP 接口。"""
    def decorator(func):
        if not ENABLE_PUBLIC_API:
            return func
        return getattr(app, method)(path)(func)

    return decorator


@public_api_route("get", "/api/categories")
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


@public_api_route("get", "/api/event-categories")
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


@public_api_route("get", "/api/channels")
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


@public_api_route("get", "/api/admin/categories")
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


@public_api_route("post", "/api/admin/categories")
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


@public_api_route("put", "/api/admin/categories/{category_id}")
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


@public_api_route("get", "/api/admin/channels")
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


@public_api_route("post", "/api/admin/channels")
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
            is_active=payload.is_active,
        )
        _apply_channel_schedule_config(channel, payload)
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


@public_api_route("put", "/api/admin/channels/{channel_id}")
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
        _apply_channel_schedule_config(channel, payload)
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


@public_api_route("get", "/api/admin/llm-model-configs")
def admin_list_llm_model_configs():
    """返回大模型配置列表，API Key 脱敏展示。"""
    session = get_session()
    try:
        return {
            "code": 0,
            "message": "success",
            "data": list_llm_model_configs(session),
        }
    finally:
        session.close()


@public_api_route("post", "/api/admin/llm-model-configs")
def admin_create_llm_model_config(payload: LLMModelConfigPayload):
    """新增大模型配置。"""
    session = get_session()
    try:
        config = create_llm_model_config(session, payload.model_dump())
        return {
            "code": 0,
            "message": "success",
            "data": next(item for item in list_llm_model_configs(session) if item["id"] == config.id),
        }
    finally:
        session.close()


@public_api_route("put", "/api/admin/llm-model-configs/{config_id}")
def admin_update_llm_model_config(config_id: int, payload: LLMModelConfigPayload):
    """更新大模型配置；api_key 为空时保留原密钥。"""
    session = get_session()
    try:
        config = update_llm_model_config(session, config_id, payload.model_dump())
        if not config:
            raise HTTPException(status_code=404, detail="大模型配置不存在")
        return {
            "code": 0,
            "message": "success",
            "data": next(item for item in list_llm_model_configs(session) if item["id"] == config.id),
        }
    finally:
        session.close()


@app.post("/api/internal/llm/chat-test")
def internal_llm_chat_test(payload: LLMChatTestPayload):
    """供 info-serve 管理后台代理调用的大模型连通性测试接口。"""
    result = run_llm_chat_test(
        prompt=payload.prompt,
        config_id=payload.config_id,
        timeout_seconds=payload.timeout_seconds,
    )
    if not result.get("ok"):
        return {
            "code": 1,
            "message": result.get("message") or "大模型调用失败",
            "data": result,
        }
    return {
        "code": 0,
        "message": "success",
        "data": result,
    }


@app.post("/api/internal/llm/chat")
def internal_llm_chat(payload: LLMChatPayload):
    """供 info-serve 管理后台代理调用的大模型普通对话接口。"""
    result = run_llm_chat_completion(
        prompt=payload.message,
        config_id=payload.config_id,
        timeout_seconds=payload.timeout_seconds,
    )
    if not result.get("ok"):
        return {
            "code": 1,
            "message": result.get("message") or "大模型对话失败",
            "data": result,
        }
    return {
        "code": 0,
        "message": "success",
        "data": result,
    }


@public_api_route("get", "/api/infos")
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
                "items": [_info_with_quality(item) for item in items],
            },
        }
    finally:
        session.close()


@public_api_route("get", "/api/events")
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
                        # 历史脉络字段
                        "previous_event_id": item.previous_event_id,
                        "event_generation": item.event_generation or 1,
                        "evolution_stage": item.evolution_stage or "emerging",
                    }
                    for item in items
                ],
            },
        }
    finally:
        session.close()


@public_api_route("get", "/api/infos/{info_id}")
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
            "data": _info_with_quality(info),
        }
    finally:
        session.close()


@public_api_route("get", "/api/events/{event_id}")
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
        evidence_chain = _build_event_evidence_chain(source_rows)

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
                    # 历史脉络字段
                    "previous_event_id": event.previous_event_id,
                    "event_generation": event.event_generation or 1,
                    "evolution_stage": event.evolution_stage or "emerging",
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
                        "quality_level": quality["quality_level"],
                        "quality_summary": quality["summary"],
                    }
                    for _, info, channel in source_rows[:6]
                    for quality in [_source_quality(info)]
                ],
                "tech_context": tech_context,
                "evidence_chain": evidence_chain,
            },
        }
    finally:
        session.close()


@public_api_route("get", "/api/admin/events/{event_id}/analysis-runs")
def get_event_analysis_runs(event_id: int):
    """
    获取事件的历次分析运行记录。
    用于追溯事件分析的完整历史。
    """
    session = get_session()
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="事件不存在")

        runs = (
            session.query(EventAnalysisRun)
            .filter(EventAnalysisRun.event_id == event_id)
            .order_by(EventAnalysisRun.created_at.desc())
            .all()
        )

        return {
            "code": 0,
            "message": "success",
            "data": {
                "event_id": event_id,
                "event_title": event.title,
                "runs": [
                    {
                        "run_id": run.id,
                        "analysis_version": run.analysis_version,
                        "mode": run.mode,
                        "provider": run.provider,
                        "model_name": run.model_name,
                        "status": run.status,
                        "input_item_count": run.input_item_count,
                        "quality_score": run.quality_score,
                        "confidence": run.confidence,
                        "fallback_used": bool(run.fallback_used),
                        "failure_reason": run.failure_reason,
                        "started_at": run.started_at.strftime("%Y-%m-%d %H:%M:%S") if run.started_at else None,
                        "finished_at": run.finished_at.strftime("%Y-%m-%d %H:%M:%S") if run.finished_at else None,
                        "created_at": run.created_at.strftime("%Y-%m-%d %H:%M:%S") if run.created_at else None,
                    }
                    for run in runs
                ],
            },
        }
    finally:
        session.close()


@public_api_route("get", "/api/admin/events/{event_id}/analysis-sources")
def get_event_analysis_sources(event_id: int, run_id: int = None):
    """
    获取事件分析运行的来源明细。

    - 不传 run_id：返回最新一次分析运行的来源
    - 传 run_id：返回指定分析运行的来源
    """
    session = get_session()
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="事件不存在")

        if run_id:
            target_run = session.query(EventAnalysisRun).filter(
                EventAnalysisRun.id == run_id,
                EventAnalysisRun.event_id == event_id,
            ).first()
            if not target_run:
                raise HTTPException(status_code=404, detail="分析运行不存在")
        else:
            target_run = session.query(EventAnalysisRun).filter(
                EventAnalysisRun.event_id == event_id,
            ).order_by(EventAnalysisRun.created_at.desc()).first()
            if not target_run:
                raise HTTPException(status_code=404, detail="暂无分析记录")

        sources = (
            session.query(EventAnalysisSource, Info, Channel)
            .outerjoin(Info, Info.id == EventAnalysisSource.info_id)
            .outerjoin(Channel, Channel.id == Info.channel_id)
            .filter(EventAnalysisSource.run_id == target_run.id)
            .order_by(EventAnalysisSource.weight.desc())
            .all()
        )

        return {
            "code": 0,
            "message": "success",
            "data": {
                "event_id": event_id,
                "event_title": event.title,
                "run": {
                    "run_id": target_run.id,
                    "mode": target_run.mode,
                    "provider": target_run.provider,
                    "model_name": target_run.model_name,
                    "status": target_run.status,
                    "quality_score": target_run.quality_score,
                    "confidence": target_run.confidence,
                    "created_at": target_run.created_at.strftime("%Y-%m-%d %H:%M:%S") if target_run.created_at else None,
                },
                "sources": [
                    {
                        "source_id": source.id,
                        "info_id": info.id if info else source.info_id,
                        "title": info.title if info else source.info_title,
                        "role": source.role,
                        "weight": source.weight,
                        "quality_score": source.quality_score,
                        "channel_name": channel.name if channel else None,
                        "source_url": info.source_url if info else None,
                        "event_time": info.event_time.strftime("%Y-%m-%d %H:%M:%S") if info and info.event_time else None,
                    }
                    for source, info, channel in sources
                ],
            },
        }
    finally:
        session.close()


@public_api_route("get", "/api/stats")
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


@public_api_route("post", "/api/admin/rebuild-events")
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


@public_api_route("post", "/api/admin/refresh-quality")
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


@public_api_route("post", "/api/admin/retry-low-quality-details")
def admin_retry_low_quality_details(limit: int = Query(20, ge=1, le=50, description="本次最多重抓的低完整内容数量")):
    """按渠道重抓低完整详情，解决详情页正文缺失或质量分偏低的问题。"""
    from scheduler import _fetch_details_for_items

    session = get_session()
    try:
        candidates = (
            session.query(Info)
            .join(Channel, Channel.id == Info.channel_id)
            .filter(Info.is_deleted == 0)
            .order_by(Info.updated_at.desc(), Info.id.desc())
            .limit(limit * 5)
            .all()
        )
        selected = []
        for info in candidates:
            profile = build_acquisition_quality_profile(info)
            if not profile.should_enqueue_detail_job:
                continue
            selected.append((info, profile))

        selected.sort(key=lambda item: (-item[1].attention_priority, item[1].completeness_score, item[0].id))
        selected = selected[:limit]
        infos = [info for info, _ in selected]
        selected_samples = [
            {
                "info_id": info.id,
                "title": info.title,
                "channel_code": info.channel.code if info.channel else "",
                "attention_priority": profile.attention_priority,
                "quality_level": profile.quality_level,
                "risk_reasons": profile.risk_reasons,
                "recommended_action": profile.recommended_action,
                "quality_summary": profile.summary,
            }
            for info, profile in selected
        ]
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
                "selected_samples": selected_samples,
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


@public_api_route("get", "/api/admin/data-quality-report")
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


@public_api_route("get", "/api/admin/channel-quality-report")
def admin_channel_quality_report(
    sample_limit: int = Query(5, ge=1, le=20, description="每个渠道返回的低质量样本数量"),
):
    """按渠道返回真实详情完整度、可用率、失败原因和凭证健康状态。"""
    session = get_session()
    try:
        return {
            "code": 0,
            "message": "success",
            "data": build_channel_quality_report(session, sample_limit=sample_limit),
        }
    finally:
        session.close()


@public_api_route("get", "/api/admin/event-analysis-quality-report")
def admin_event_analysis_quality_report(
    limit: int = Query(20, ge=1, le=100, description="返回的风险事件数量"),
):
    """返回事件分析质量报告，帮助运营发现低置信度、回退和弱来源事件。"""
    session = get_session()
    try:
        return {
            "code": 0,
            "message": "success",
            "data": build_event_analysis_quality_report(session, limit=limit),
        }
    finally:
        session.close()


@public_api_route("post", "/api/admin/event-analysis-detail-jobs")
def admin_enqueue_event_analysis_detail_jobs(
    limit: int = Query(20, ge=1, le=100, description="本次最多入队的弱来源数量"),
):
    """将事件分析质量风险中的弱来源加入详情补偿队列。"""
    session = get_session()
    try:
        result = enqueue_event_analysis_detail_jobs(session, limit=limit)
        return {
            "code": 0,
            "message": "事件分析弱来源已加入详情补偿队列",
            "data": result,
        }
    finally:
        session.close()


@public_api_route("post", "/api/admin/prioritize-source-quality-governance")
def admin_prioritize_source_quality_governance(
    limit: int = Query(20, ge=1, le=100, description="本次最多治理的风险来源数量"),
):
    """一键治理来源质量风险：定向补偿弱来源、补事实源、重分析并刷新展示质量。"""
    session = get_session()
    try:
        result = prioritize_source_quality_governance(session, limit=limit)
        return {
            "code": 0,
            "message": "来源质量风险已完成优先治理",
            "data": result,
        }
    finally:
        session.close()


@public_api_route("post", "/api/admin/rebuild-stale-event-analysis")
def admin_rebuild_stale_event_analysis(
    limit: int = Query(200, ge=1, le=1000, description="事件重建最多读取的信息数量"),
):
    """手动处理过期事件分析，供运营在详情补偿后立即刷新事件摘要。"""
    session = get_session()
    try:
        result = rebuild_stale_event_analysis(session, limit=limit)
        return {
            "code": 0,
            "message": "过期事件分析已处理",
            "data": result,
        }
    finally:
        session.close()


@public_api_route("post", "/api/admin/mark-low-confidence-event-analysis-stale")
def admin_mark_low_confidence_event_analysis_stale(
    limit: int = Query(100, ge=1, le=1000, description="本次最多标记的低置信完整来源事件数量"),
):
    """将低置信但来源已完整可用的事件标记为过期，供后续重分析。"""
    session = get_session()
    try:
        result = mark_low_confidence_complete_events_stale(session, limit=limit)
        return {
            "code": 0,
            "message": "低置信完整来源事件已标记为待重分析",
            "data": result,
        }
    finally:
        session.close()


@public_api_route("get", "/api/admin/crawl-credential-report")
def admin_crawl_credential_report():
    """返回采集凭证脱敏健康状态，帮助判断弱渠道是否因为 Cookie 缺失或过期。"""
    session = get_session()
    try:
        channel_codes = [channel.code for channel in session.query(Channel).order_by(Channel.id.asc()).all()]
        return {
            "code": 0,
            "message": "success",
            "data": build_credential_report(channel_codes),
        }
    finally:
        session.close()


@public_api_route("get", "/api/admin/channels/{channel_code}/credentials")
def admin_get_channel_credentials(channel_code: str):
    """获取渠道凭证信息（脱敏）。"""
    from services.collection.credential_provider import CredentialProvider

    provider = CredentialProvider.get_instance()
    info = provider.get_channel_credential_info(channel_code)

    if info is None:
        return {
            "code": 1,
            "message": f"渠道 {channel_code} 不存在或无法获取凭证信息",
            "data": None,
        }

    return {
        "code": 0,
        "message": "success",
        "data": {
            "channel_code": info.channel_code,
            "cookie_configured": info.cookie_configured,
            "cookie_preview": info.cookie_preview,
            "cookie_status": info.cookie_status,
            "extra_credentials": info.extra_credentials,
            "updated_at": info.updated_at,
            "updated_by": info.updated_by,
        },
    }


@public_api_route("put", "/api/admin/channels/{channel_code}/credentials")
def admin_update_channel_credentials(channel_code: str, payload: ChannelCredentialPayload):
    """更新渠道凭证（Cookie 和扩展凭证）。"""
    from services.collection.credential_provider import CredentialProvider

    provider = CredentialProvider.get_instance()
    success = provider.update_channel_credentials(
        channel_code=channel_code,
        cookies=payload.cookies if payload.cookies else None,
        extra_credentials=payload.extra_credentials,
        updated_by=payload.updated_by,
    )

    if not success:
        return {
            "code": 1,
            "message": f"渠道 {channel_code} 不存在或更新失败",
            "data": None,
        }

    return {
        "code": 0,
        "message": "凭证更新成功",
        "data": {"channel_code": channel_code},
    }


@public_api_route("post", "/api/admin/channels/{channel_code}/credentials/test")
def admin_test_channel_credentials(channel_code: str):
    """测试渠道凭证有效性。"""
    from services.collection.credential_provider import CredentialProvider

    supported_channels = ["weibo", "zhihu", "xiaohongshu"]
    if channel_code not in supported_channels:
        return {
            "code": 1,
            "message": f"不支持验证渠道 {channel_code}，支持的渠道: {', '.join(supported_channels)}",
            "data": None,
        }

    provider = CredentialProvider.get_instance()
    result = provider.verify_credential(channel_code)

    return {
        "code": 0 if result["success"] else 1,
        "message": result["message"],
        "data": {
            "channel_code": channel_code,
            "success": result["success"],
            "response_code": result["response_code"],
        },
    }


@public_api_route("delete", "/api/admin/channels/{channel_code}/credentials")
def admin_delete_channel_credentials(channel_code: str):
    """清除渠道凭证。"""
    from services.collection.credential_provider import CredentialProvider

    provider = CredentialProvider.get_instance()
    success = provider.delete_channel_credentials(channel_code)

    if not success:
        return {
            "code": 1,
            "message": f"渠道 {channel_code} 不存在或清除失败",
            "data": None,
        }

    return {
        "code": 0,
        "message": "凭证已清除",
        "data": {"channel_code": channel_code},
    }


@public_api_route("get", "/api/admin/detail-jobs")
def admin_detail_jobs(
    sample_limit: int = Query(10, ge=1, le=50, description="每类任务样本数量"),
    channel_code: str = Query("", max_length=80, description="按渠道编码过滤"),
    failure_reason: str = Query("", max_length=200, description="按失败原因过滤"),
):
    """返回详情补偿队列概览，辅助定位积压渠道和失败原因。"""
    session = get_session()
    try:
        return {
            "code": 0,
            "message": "success",
            "data": build_detail_job_report(
                session,
                sample_limit=sample_limit,
                channel_code=channel_code.strip(),
                failure_reason=failure_reason.strip(),
            ),
        }
    finally:
        session.close()


@public_api_route("post", "/api/admin/archive-low-quality")
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


@public_api_route("post", "/api/admin/archive-duplicate-titles")
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


@public_api_route("post", "/api/crawl/trigger")
def trigger_crawl(
    background_tasks: BackgroundTasks,
    channel_code: str = Query(..., description="渠道编码"),
):
    """
    手动触发指定渠道的爬取任务
    参数:
        channel_code: 渠道编码
    返回: 爬取结果
    """
    from crawlers.registry import crawler_registry
    crawler = crawler_registry.get(channel_code)
    if not crawler:
        raise HTTPException(status_code=404, detail=f"渠道 {channel_code} 未注册")

    background_tasks.add_task(_run_manual_crawl, channel_code)

    return {
        "code": 0,
        "message": "采集任务已提交，后台执行中",
        "data": {
            "channel": channel_code,
            "status": "accepted",
            "trigger_type": "manual",
        },
    }

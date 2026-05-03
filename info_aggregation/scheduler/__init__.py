"""
信息聚合系统 - 定时任务模块
使用APScheduler实现定时爬取调度
"""
import logging
import time
import random
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import or_

from config import (
    SCHEDULER_HOT_INTERVAL,
    SCHEDULER_ECONOMY_INTERVAL,
    SCHEDULER_INTERNATIONAL_INTERVAL,
    SCHEDULER_TECH_INTERVAL,
    SCHEDULER_AI_INTERVAL,
    CATEGORY_HOT,
    CATEGORY_ECONOMY,
    CATEGORY_INTERNATIONAL,
    CATEGORY_TECH,
    CATEGORY_AI,
    CATEGORY_SPORTS,
)
from crawlers.registry import crawler_registry
from cleaners import clean_info_list
from database import get_session, Channel, CrawlRunLog, CrawlTask, Info, InfoAcquisitionLog
from services.data_quality import is_low_quality_list_item, is_near_duplicate_item, is_title_content_duplicate
from services import parse_tech_content, rebuild_events
from services.data_quality_report import save_data_quality_snapshot
from services.detail_jobs import enqueue_low_quality_detail_jobs
from services.detail_job_worker import crawler_detail_runner, process_pending_detail_jobs
from services.detail_pipeline import DetailStrategyResult, run_detail_pipeline

logger = logging.getLogger(__name__)


def _apply_info_semantics(info: Info, content: str):
    """用最终正文补齐轻量语义字段，保证列表嵌入详情和二次详情路径一致。"""
    semantic_result = parse_tech_content(info.title, content or info.content or "")
    info.tech_topic_type = semantic_result.topic_type
    info.tech_entities = ",".join(semantic_result.entities)
    info.tech_keywords = ",".join(semantic_result.keywords)


def _record_info_acquisition_log(
    session,
    info: Info,
    channel_code: str,
    strategy: str,
    status: str,
    score: int,
    content_length: int,
    failure_reason: str,
    matched_rules: list[str],
    content: str,
):
    """记录详情采集结果，供质量诊断和后续 replay 使用。"""
    session.add(
        InfoAcquisitionLog(
            info_id=info.id,
            channel_code=channel_code,
            strategy=strategy,
            status=status,
            score=score,
            content_length=content_length,
            failure_reason=failure_reason,
            matched_rules=",".join(matched_rules),
            raw_excerpt=(content or info.content or "")[:200],
        )
    )


def _effective_channel_interval(channel: Channel) -> int:
    """返回调度器实际使用的分钟间隔，兼容尚未配置 Max 字段的历史渠道。"""
    effective_interval = channel.effective_interval_minutes
    legacy_interval = channel.crawl_interval or 60
    # 新字段上线前的老渠道只有 crawl_interval；如果 Max 字段仍是默认值，
    # 继续使用老间隔，避免调度同步后被默认 60 分钟覆盖。
    if (
        effective_interval == 60
        and legacy_interval != 60
        and (channel.base_interval_minutes in (None, 60))
    ):
        return legacy_interval
    return effective_interval or legacy_interval


def _sync_crawl_tasks(session) -> dict:
    """把启用渠道同步为 Pro 监控后台可见的采集任务。"""
    created_count = 0
    updated_count = 0
    now = datetime.now()
    channels = session.query(Channel).filter(Channel.is_active == 1).all()
    for channel in channels:
        task_code = f"crawl_{channel.code}"
        task = session.query(CrawlTask).filter(CrawlTask.task_code == task_code).first()
        interval = _effective_channel_interval(channel)
        schedule_version = channel.schedule_version or 1
        if not task:
            task = CrawlTask(
                channel_id=channel.id,
                task_code=task_code,
                task_name=f"{channel.name}采集",
                schedule_type="interval",
                schedule_value=str(interval),
                schedule_version=schedule_version,
                status="active",
                next_run_at=now,
            )
            session.add(task)
            created_count += 1
        else:
            previous_value = task.schedule_value
            previous_version = task.schedule_version or 0
            task.channel_id = channel.id
            task.task_name = f"{channel.name}采集"
            task.schedule_type = "interval"
            task.schedule_value = str(interval)
            task.schedule_version = schedule_version
            task.status = "active"
            if previous_value != str(interval) or previous_version != schedule_version:
                task.next_run_at = now + timedelta(minutes=interval)
            updated_count += 1
    session.commit()
    return {"created_count": created_count, "updated_count": updated_count}


def _get_due_channel_codes(session, category_id: int, now: datetime | None = None) -> list[str]:
    """返回当前分类下已经到期的渠道编码。"""
    now = now or datetime.now()
    due_tasks = (
        session.query(CrawlTask)
        .join(Channel, CrawlTask.channel_id == Channel.id)
        .filter(
            Channel.category_id == category_id,
            Channel.is_active == 1,
            CrawlTask.status == "active",
            or_(CrawlTask.next_run_at.is_(None), CrawlTask.next_run_at <= now),
        )
        .order_by(CrawlTask.next_run_at.asc(), CrawlTask.id.asc())
        .all()
    )
    return [task.channel.code for task in due_tasks if task.channel]


def _record_crawl_run(
    session,
    channel_code: str,
    trigger_type: str,
    status: str,
    raw_count: int,
    cleaned_count: int,
    saved_count: int,
    detail_success_count: int,
    detail_failed_count: int,
    error_message: str,
    started_at: datetime,
    finished_at: datetime,
):
    """写入单次采集运行日志，供 Pro 管理后台展示。"""
    task = session.query(CrawlTask).filter(CrawlTask.task_code == f"crawl_{channel_code}").first()
    if task:
        task.last_run_at = finished_at
        try:
            interval_minutes = int(task.schedule_value or "0")
        except ValueError:
            interval_minutes = 0
        if interval_minutes > 0:
            task.next_run_at = finished_at + timedelta(minutes=interval_minutes)
    session.add(
        CrawlRunLog(
            task_id=task.id if task else None,
            channel_code=channel_code,
            trigger_type=trigger_type,
            status=status,
            raw_count=raw_count,
            cleaned_count=cleaned_count,
            saved_count=saved_count,
            detail_success_count=detail_success_count,
            detail_failed_count=detail_failed_count,
            error_message=error_message[:1000],
            started_at=started_at,
            finished_at=finished_at,
        )
    )
    session.commit()


def _get_channel_category_map() -> dict:
    """
    从数据库获取渠道编码到分类ID的映射
    返回: {channel_code: category_id} 字典
    """
    session = get_session()
    try:
        channels = session.query(Channel).all()
        return {ch.code: ch.id for ch in channels}
    finally:
        session.close()


def _get_category_id_map() -> dict:
    """
    从数据库获取分类名称到分类ID的映射
    返回: {category_name: category_id} 字典
    """
    session = get_session()
    try:
        from database import Category
        categories = session.query(Category).all()
        return {cat.name: cat.id for cat in categories}
    finally:
        session.close()


def _save_crawled_data(channel_code: str, items: list) -> list:
    """
    将爬取并清洗后的数据保存到数据库
    参数:
        channel_code: 渠道编码
        items: 清洗后的信息列表
    返回:
        新保存的Info对象ID列表，用于后续详情爬取
    """
    if not items:
        return []

    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.code == channel_code).first()
        if not channel:
            logger.warning(f"渠道 {channel_code} 不存在于数据库")
            return []

        saved_ids = []
        saved_count = 0
        recent_existing = (
            session.query(Info)
            .filter(Info.channel_id == channel.id)
            .order_by(Info.created_at.desc())
            .limit(200)
            .all()
        )
        for item in items:
            existing = session.query(Info).filter(
                Info.source_id == item["source_id"],
                Info.channel_id == channel.id,
            ).first()

            if existing:
                continue
            if any(
                is_near_duplicate_item(
                    item["title"],
                    item["content"],
                    existing_item.title,
                    existing_item.content,
                )
                for existing_item in recent_existing
            ):
                logger.info(f"渠道 {channel_code}: 跳过近似重复内容 {item['title'][:30]}")
                continue

            detail_status = "pending"
            detail_error = ""
            detail_strategy = ""
            detail_score = 0
            detail_content_length = 0
            detail_fetched_at = None
            content = item["content"]
            embedded_pipeline = None
            embedded_content = item.get("_search_content")
            if embedded_content:
                embedded_pipeline = run_detail_pipeline(
                    title=item["title"],
                    list_content=item["content"],
                    strategy_results=[
                        DetailStrategyResult(strategy="search_embedded", content=embedded_content)
                    ],
                    channel_code=channel_code,
                )
                if embedded_pipeline.status == "complete":
                    content = embedded_pipeline.content
                    detail_status = embedded_pipeline.status
                    detail_error = embedded_pipeline.failure_reason
                    detail_strategy = embedded_pipeline.strategy
                    detail_score = embedded_pipeline.score
                    detail_content_length = embedded_pipeline.content_length
                    detail_fetched_at = datetime.now()
                else:
                    embedded_pipeline = None

            info = Info(
                title=item["title"],
                content=content,
                category_id=channel.category_id,
                channel_id=channel.id,
                source_id=item["source_id"],
                source_url=item["source_url"],
                event_time=item["event_time"],
                core_entity=item.get("core_entity", ""),
                location=item.get("location", ""),
                indicator_name=item.get("indicator_name", ""),
                indicator_value=item.get("indicator_value", ""),
                detail_fetch_status=detail_status,
                detail_fetch_error=detail_error,
                detail_strategy=detail_strategy,
                detail_score=detail_score,
                detail_content_length=detail_content_length,
                detail_fetched_at=detail_fetched_at,
            )
            session.add(info)
            session.flush()
            if embedded_pipeline:
                _apply_info_semantics(info, content)
                _record_info_acquisition_log(
                    session,
                    info=info,
                    channel_code=channel_code,
                    strategy=embedded_pipeline.strategy,
                    status=embedded_pipeline.status,
                    score=embedded_pipeline.score,
                    content_length=embedded_pipeline.content_length,
                    failure_reason=embedded_pipeline.failure_reason,
                    matched_rules=embedded_pipeline.matched_rules,
                    content=content,
                )
            saved_ids.append(info.id)
            recent_existing.insert(0, info)
            saved_count += 1

        session.commit()
        logger.info(f"渠道 {channel_code}: 保存{saved_count}条新信息")
        return saved_ids
    except Exception as e:
        session.rollback()
        logger.error(f"保存数据失败: {e}", exc_info=True)
        return []
    finally:
        session.close()


def _fetch_details_for_items(channel_code: str, saved_ids: list):
    """
    对新保存的信息执行详情页爬取，更新content和详情爬取状态
    爬取失败时保留原始content，并标注失败原因
    参数:
        channel_code: 渠道编码
        saved_ids: 需要爬取详情的Info记录ID列表
    """
    if not saved_ids:
        return {"detail_success_count": 0, "detail_failed_count": 0}

    crawler = crawler_registry.get(channel_code)
    if not crawler:
        logger.warning(f"渠道 {channel_code} 爬虫未注册，跳过详情爬取")
        return {"detail_success_count": 0, "detail_failed_count": len(saved_ids)}

    session = get_session()
    detail_success_count = 0
    detail_failed_count = 0
    try:
        for info_id in saved_ids:
            info = session.query(Info).filter(Info.id == info_id).first()
            if not info:
                continue

            original_content = info.content or ""
            if (
                info.detail_fetch_status == "complete"
                and (info.detail_score or 0) >= 80
                and (info.detail_content_length or len(original_content)) >= 40
            ):
                detail_success_count += 1
                logger.info(
                    f"详情已完整，跳过重复爬取 [ID={info_id}] "
                    f"策略={info.detail_strategy}: 内容{info.detail_content_length or len(original_content)}字"
                )
                if not (info.tech_topic_type or info.tech_entities or info.tech_keywords):
                    _apply_info_semantics(info, original_content)
                if (
                    session.query(InfoAcquisitionLog)
                    .filter(InfoAcquisitionLog.info_id == info.id)
                    .count()
                    == 0
                ):
                    _record_info_acquisition_log(
                        session,
                        info=info,
                        channel_code=channel_code,
                        strategy=info.detail_strategy or "complete_skip",
                        status=info.detail_fetch_status,
                        score=info.detail_score or 0,
                        content_length=info.detail_content_length or len(original_content),
                        failure_reason=info.detail_fetch_error or "",
                        matched_rules=["already_complete"],
                        content=original_content,
                    )
                continue

            with crawler_registry.get_lock(channel_code):
                detail_content, status, error_msg, pipeline = crawler.safe_fetch_detail(
                    info.source_url, info.to_dict()
                )
            if detail_content and is_title_content_duplicate(info.title, detail_content):
                detail_content = ""
                status = "list_only"
                error_msg = "title_content_duplicate"
                pipeline.content = original_content
                pipeline.status = status
                pipeline.failure_reason = error_msg
                pipeline.score = min(pipeline.score, 10)
                pipeline.content_length = len(original_content)
                pipeline.matched_rules = [*pipeline.matched_rules, "title_content_duplicate"]
            elif detail_content and is_low_quality_list_item(info.title, detail_content):
                detail_content = ""
                status = "list_only"
                error_msg = "low_quality_detail"
                pipeline.content = original_content
                pipeline.status = status
                pipeline.failure_reason = error_msg
                pipeline.score = min(pipeline.score, 10)
                pipeline.content_length = len(original_content)
                pipeline.matched_rules = [*pipeline.matched_rules, "low_quality_detail"]

            if detail_content:
                info.content = detail_content
            info.detail_fetch_status = status
            info.detail_fetch_error = error_msg
            info.detail_strategy = pipeline.strategy
            info.detail_score = pipeline.score
            info.detail_content_length = pipeline.content_length
            info.detail_fetched_at = datetime.now()
            _apply_info_semantics(info, detail_content or original_content)
            _record_info_acquisition_log(
                session,
                info=info,
                channel_code=channel_code,
                strategy=pipeline.strategy,
                status=status,
                score=pipeline.score,
                content_length=pipeline.content_length,
                failure_reason=error_msg,
                matched_rules=pipeline.matched_rules,
                content=detail_content or original_content,
            )

            if status in {"partial", "complete"} and detail_content:
                detail_success_count += 1
                logger.info(f"详情爬取成功 [ID={info_id}] 策略={pipeline.strategy}: 内容{len(detail_content)}字")
            else:
                detail_failed_count += 1
                logger.warning(f"详情爬取未完成 [ID={info_id}] 状态={status}: {error_msg}，保留内容({len((detail_content or original_content))}字)")

            time.sleep(random.uniform(1.0, 3.0))

        session.commit()
        logger.info(f"渠道 {channel_code}: 详情爬取完成，共处理{len(saved_ids)}条")
        return {
            "detail_success_count": detail_success_count,
            "detail_failed_count": detail_failed_count,
        }
    except Exception as e:
        session.rollback()
        logger.error(f"详情爬取过程异常: {e}", exc_info=True)
        return {
            "detail_success_count": detail_success_count,
            "detail_failed_count": len(saved_ids) - detail_success_count,
        }
    finally:
        session.close()


def crawl_by_category(category_name: str):
    """
    按分类执行爬取任务
    参数:
        category_name: 分类名称
    """
    logger.info(f"开始执行分类 [{category_name}] 的爬取任务")
    all_crawlers = crawler_registry.get_all()

    category_id_map = _get_category_id_map()
    target_category_id = category_id_map.get(category_name)
    if not target_category_id:
        logger.warning(f"分类 {category_name} 不存在")
        return

    session = get_session()
    try:
        _sync_crawl_tasks(session)
        channels = session.query(Channel).filter(
            Channel.category_id == target_category_id,
            Channel.is_active == 1,
        ).all()
        active_codes = {ch.code for ch in channels}
        due_codes = set(_get_due_channel_codes(session, target_category_id))
    finally:
        session.close()

    for code, crawler in all_crawlers.items():
        if code not in active_codes or code not in due_codes:
            continue
        started_at = datetime.now()
        raw_count = 0
        cleaned_count = 0
        saved_count = 0
        detail_result = {"detail_success_count": 0, "detail_failed_count": 0}
        status = "success"
        error_message = ""
        try:
            with crawler_registry.get_lock(code):
                raw_items = crawler.safe_crawl()
            raw_count = len(raw_items)
            cleaned_items = clean_info_list(raw_items)
            cleaned_count = len(cleaned_items)
            saved_ids = _save_crawled_data(code, cleaned_items)
            saved_count = len(saved_ids)
            detail_result = _fetch_details_for_items(code, saved_ids)
            if detail_result["detail_failed_count"] > 0:
                status = "partial"
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            logger.error(f"渠道 {code} 采集失败: {exc}", exc_info=True)
        finally:
            monitor_session = get_session()
            try:
                _sync_crawl_tasks(monitor_session)
                _record_crawl_run(
                    monitor_session,
                    channel_code=code,
                    trigger_type="scheduler",
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
            finally:
                monitor_session.close()

    session = get_session()
    try:
        rebuild_events(session)
        save_data_quality_snapshot(session)
    finally:
        session.close()

    logger.info(f"分类 [{category_name}] 爬取任务完成")


def crawl_hot():
    """热点事件爬取任务（每30分钟）"""
    crawl_by_category(CATEGORY_HOT)


def crawl_economy():
    """经济数据爬取任务（每1小时）"""
    crawl_by_category(CATEGORY_ECONOMY)


def crawl_international():
    """国际大事爬取任务（每2小时）"""
    crawl_by_category(CATEGORY_INTERNATIONAL)


def crawl_tech():
    """科技动向爬取任务（每2小时）"""
    crawl_by_category(CATEGORY_TECH)


def crawl_ai():
    """AI大模型动向爬取任务（每2小时）"""
    crawl_by_category(CATEGORY_AI)


def crawl_sports():
    """体育新闻爬取任务（每1小时）"""
    crawl_by_category(CATEGORY_SPORTS)


def cleanup_expired_infos():
    """
    清理两周前创建的信息数据
    """
    cutoff = datetime.now() - timedelta(days=14)
    session = get_session()
    try:
        deleted_count = (
            session.query(Info)
            .filter(Info.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        session.commit()
        logger.info(f"历史数据清理完成，删除{deleted_count}条，截止时间: {cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        session.rollback()
        logger.error(f"历史数据清理失败: {e}", exc_info=True)
    finally:
        session.close()


def process_detail_jobs(session=None, runner=None, enqueue_limit: int = 100, process_limit: int = 20) -> dict:
    """入队并处理详情补偿任务，供 scheduler 和测试共用。"""

    owns_session = session is None
    session = session or get_session()
    try:
        enqueue_result = enqueue_low_quality_detail_jobs(session, limit=enqueue_limit)
        process_result = process_pending_detail_jobs(
            session,
            runner=runner or crawler_detail_runner,
            limit=process_limit,
        )
        return {"enqueue": enqueue_result, "process": process_result}
    finally:
        if owns_session:
            session.close()


def setup_scheduler() -> BackgroundScheduler:
    """
    初始化并配置定时任务调度器
    返回: 配置好的BackgroundScheduler实例
    """
    scheduler = BackgroundScheduler()
    session = get_session()
    try:
        _sync_crawl_tasks(session)
    finally:
        session.close()

    scheduler.add_job(
        crawl_hot,
        trigger=IntervalTrigger(minutes=SCHEDULER_HOT_INTERVAL),
        id="crawl_hot",
        name="热点事件爬取",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        crawl_economy,
        trigger=IntervalTrigger(minutes=SCHEDULER_ECONOMY_INTERVAL),
        id="crawl_economy",
        name="经济数据爬取",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        crawl_international,
        trigger=IntervalTrigger(minutes=SCHEDULER_INTERNATIONAL_INTERVAL),
        id="crawl_international",
        name="国际大事爬取",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        crawl_tech,
        trigger=IntervalTrigger(minutes=SCHEDULER_TECH_INTERVAL),
        id="crawl_tech",
        name="科技动向爬取",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        crawl_ai,
        trigger=IntervalTrigger(minutes=SCHEDULER_AI_INTERVAL),
        id="crawl_ai",
        name="AI大模型动向爬取",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        crawl_sports,
        trigger=IntervalTrigger(minutes=60),
        id="crawl_sports",
        name="体育新闻爬取",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        cleanup_expired_infos,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_expired_infos",
        name="清理两周前历史数据",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        process_detail_jobs,
        trigger=IntervalTrigger(minutes=10),
        id="process_detail_jobs",
        name="详情补偿队列处理",
        max_instances=1,
        misfire_grace_time=300,
    )

    logger.info("定时任务调度器配置完成")
    return scheduler

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
)
from crawlers.registry import crawler_registry
from cleaners import clean_info_list
from database import get_session, Channel, Info, InfoAcquisitionLog
from services.data_quality import is_low_quality_list_item, is_near_duplicate_item, is_title_content_duplicate
from services import parse_tech_content, rebuild_events

logger = logging.getLogger(__name__)


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

            info = Info(
                title=item["title"],
                content=item["content"],
                category_id=channel.category_id,
                channel_id=channel.id,
                source_id=item["source_id"],
                source_url=item["source_url"],
                event_time=item["event_time"],
                core_entity=item.get("core_entity", ""),
                location=item.get("location", ""),
                indicator_name=item.get("indicator_name", ""),
                indicator_value=item.get("indicator_value", ""),
                detail_fetch_status="pending",
            )
            session.add(info)
            session.flush()
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
        return

    crawler = crawler_registry.get(channel_code)
    if not crawler:
        logger.warning(f"渠道 {channel_code} 爬虫未注册，跳过详情爬取")
        return

    session = get_session()
    try:
        for info_id in saved_ids:
            info = session.query(Info).filter(Info.id == info_id).first()
            if not info:
                continue

            original_content = info.content or ""

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
            # 使用最终落库正文做轻量科技结构化，便于 Plus 阶段的详情诊断和阅读增强。
            semantic_result = parse_tech_content(info.title, detail_content or original_content)
            info.tech_topic_type = semantic_result.topic_type
            info.tech_entities = ",".join(semantic_result.entities)
            info.tech_keywords = ",".join(semantic_result.keywords)
            session.add(
                InfoAcquisitionLog(
                    info_id=info.id,
                    channel_code=channel_code,
                    strategy=pipeline.strategy,
                    status=status,
                    score=pipeline.score,
                    content_length=pipeline.content_length,
                    failure_reason=error_msg,
                    matched_rules=",".join(pipeline.matched_rules),
                    raw_excerpt=(detail_content or original_content)[:200],
                )
            )

            if status in {"partial", "complete"} and detail_content:
                logger.info(f"详情爬取成功 [ID={info_id}] 策略={pipeline.strategy}: 内容{len(detail_content)}字")
            else:
                logger.warning(f"详情爬取未完成 [ID={info_id}] 状态={status}: {error_msg}，保留内容({len((detail_content or original_content))}字)")

            time.sleep(random.uniform(1.0, 3.0))

        session.commit()
        logger.info(f"渠道 {channel_code}: 详情爬取完成，共处理{len(saved_ids)}条")
    except Exception as e:
        session.rollback()
        logger.error(f"详情爬取过程异常: {e}", exc_info=True)
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
        channels = session.query(Channel).filter(
            Channel.category_id == target_category_id,
            Channel.is_active == 1,
        ).all()
        active_codes = [ch.code for ch in channels]
    finally:
        session.close()

    for code, crawler in all_crawlers.items():
        if code not in active_codes:
            continue
        raw_items = crawler.safe_crawl()
        cleaned_items = clean_info_list(raw_items)
        saved_ids = _save_crawled_data(code, cleaned_items)
        _fetch_details_for_items(code, saved_ids)

    session = get_session()
    try:
        rebuild_events(session)
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


def setup_scheduler() -> BackgroundScheduler:
    """
    初始化并配置定时任务调度器
    返回: 配置好的BackgroundScheduler实例
    """
    scheduler = BackgroundScheduler()

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
        cleanup_expired_infos,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_expired_infos",
        name="清理两周前历史数据",
        max_instances=1,
        misfire_grace_time=300,
    )

    logger.info("定时任务调度器配置完成")
    return scheduler

"""Runtime orchestration for starting the aggregation service."""

import logging

import uvicorn

from application.crawler_bootstrap import register_all_crawlers
from application.logging_config import setup_logging
from config import API_HOST, API_PORT


def run_application():
    """Initialize storage, crawlers, scheduler, and the HTTP API."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("信息聚合系统 Info_aggregation 启动中 ...")
    logger.info("=" * 60)

    logger.info("[1/4] 初始化数据库和基础数据...")
    from sql.init_data import init_all_data
    init_all_data()
    from database import get_session
    from services.collection.credential_provider import CredentialProvider
    CredentialProvider.get_instance(session_factory=get_session)

    logger.info("[2/4] 注册爬虫模块...")
    register_all_crawlers()

    logger.info("[3/4] 启动定时任务调度器...")
    from scheduler import setup_scheduler
    scheduler = setup_scheduler()
    scheduler.start()

    logger.info("[4/4] 启动API服务...")
    from api import app

    logger.info("API服务启动于 http://%s:%s", API_HOST, API_PORT)
    logger.info("API文档地址 http://%s:%s/docs", API_HOST, API_PORT)
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")

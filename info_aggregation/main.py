"""
信息聚合系统 - 主入口
启动FastAPI服务、初始化数据库、注册爬虫、启动定时任务。

具体启动编排放在 application/ 目录，main.py 只保留进程入口和历史兼容导出。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.crawler_bootstrap import register_all_crawlers
from application.logging_config import TimezoneFormatter, setup_logging
from application.runtime import run_application


def main():
    """系统主入口"""
    run_application()


if __name__ == "__main__":
    main()

"""Crawler registration for all supported channels."""

import logging


def register_all_crawlers():
    """Register all channel crawlers with the process-local crawler registry."""
    from crawlers.cctv_sports import CctvSportsCrawler
    from crawlers.cnblogs import CnblogsCrawler
    from crawlers.csdn import CSDNCrawler
    from crawlers.eastmoney import EastmoneyCrawler
    from crawlers.juejin import JuejinCrawler
    from crawlers.kr36 import Kr36Crawler
    from crawlers.registry import crawler_registry
    from crawlers.reuters import ReutersCrawler
    from crawlers.sina_sports import SinaSportsCrawler
    from crawlers.toutiao import ToutiaoCrawler
    from crawlers.weibo import WeiboCrawler
    from crawlers.xiaohongshu import XiaohongshuCrawler
    from crawlers.zhihu import ZhihuCrawler

    crawlers = [
        WeiboCrawler(),
        ToutiaoCrawler(),
        XiaohongshuCrawler(),
        EastmoneyCrawler(),
        ReutersCrawler(),
        CSDNCrawler(),
        JuejinCrawler(),
        CnblogsCrawler(),
        Kr36Crawler(),
        ZhihuCrawler(),
        CctvSportsCrawler(),
        SinaSportsCrawler(),
    ]

    for crawler in crawlers:
        crawler_registry.register(crawler.channel_code, crawler)

    logging.getLogger(__name__).info("已注册%s个爬虫", len(crawlers))


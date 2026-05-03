"""
信息聚合系统 - 爬虫注册中心
管理所有渠道爬虫的注册与获取，支持动态扩展
"""
import logging
from threading import RLock

logger = logging.getLogger(__name__)


class CrawlerRegistry:
    """
    爬虫注册中心
    使用注册模式管理爬虫实例，新增渠道只需注册即可被调度
    """

    def __init__(self):
        self._crawlers = {}
        self._locks = {}

    def register(self, channel_code: str, crawler_instance):
        """
        注册爬虫实例
        参数:
            channel_code: 渠道编码
            crawler_instance: BaseCrawler子类实例
        """
        self._crawlers[channel_code] = crawler_instance
        self._locks.setdefault(channel_code, RLock())
        logger.info(f"已注册爬虫: {channel_code}")

    def get(self, channel_code: str):
        """
        根据渠道编码获取爬虫实例
        参数:
            channel_code: 渠道编码
        返回:
            BaseCrawler子类实例，未找到返回None
        """
        return self._crawlers.get(channel_code)

    def get_lock(self, channel_code: str):
        """获取渠道级采集锁，避免同一渠道爬虫实例被多个后台任务并发复用。"""
        return self._locks.setdefault(channel_code, RLock())

    def get_all(self) -> dict:
        """获取所有已注册的爬虫实例"""
        return self._crawlers.copy()

    def list_channels(self) -> list:
        """列出所有已注册的渠道编码"""
        return list(self._crawlers.keys())


crawler_registry = CrawlerRegistry()

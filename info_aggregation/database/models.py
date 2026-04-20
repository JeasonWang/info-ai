"""
信息聚合系统 - 数据库模型定义
使用SQLAlchemy ORM定义渠道表、分类表、信息主表
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Index, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Category(Base):
    """
    分类表：存储信息分类（热点事件/经济数据/国际大事/科技动向/AI大模型动向）
    支持动态扩展分类，新增分类只需插入记录
    """
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name = Column(String(50), nullable=False, unique=True, comment="分类名称")
    code = Column(String(50), nullable=False, unique=True, comment="分类编码")
    description = Column(String(200), default="", comment="分类描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    infos = relationship("Info", back_populates="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', code='{self.code}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


class Channel(Base):
    """
    渠道表：存储信息来源渠道（微博/头条/CSDN等）
    支持动态扩展渠道，新增渠道只需插入记录并实现对应爬虫
    """
    __tablename__ = "channel"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="渠道ID")
    name = Column(String(50), nullable=False, unique=True, comment="渠道名称")
    code = Column(String(50), nullable=False, unique=True, comment="渠道编码")
    base_url = Column(String(255), default="", comment="渠道基础URL")
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False, comment="关联分类ID")
    crawl_interval = Column(Integer, default=60, comment="爬取间隔(分钟)")
    is_active = Column(Integer, default=1, comment="是否启用 1-启用 0-禁用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    infos = relationship("Info", back_populates="channel", lazy="dynamic")
    category_rel = relationship("Category", lazy="joined")

    def __repr__(self):
        return f"<Channel(id={self.id}, name='{self.name}', code='{self.code}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "base_url": self.base_url,
            "category_id": self.category_id,
            "category_name": self.category_rel.name if self.category_rel else "",
            "crawl_interval": self.crawl_interval,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


class Info(Base):
    """
    信息主表：存储爬取到的所有信息
    通过channel_id关联渠道，通过category_id关联分类
    使用source_id+channel_id做去重唯一约束
    """
    __tablename__ = "info"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="信息ID")
    title = Column(String(200), nullable=False, comment="标题(≤40字)")
    content = Column(Text, default="", comment="内容/事件详情(150-500字)")
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False, comment="分类ID")
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False, comment="渠道ID")
    source_id = Column(String(100), default="", comment="来源唯一标识(用于去重)")
    source_url = Column(String(500), default="", comment="来源URL")
    event_time = Column(DateTime, comment="事件发生时间")
    core_entity = Column(String(100), default="", comment="核心主体/人物")
    location = Column(String(100), default="", comment="地点")
    indicator_name = Column(String(100), default="", comment="指标名称(经济数据类)")
    indicator_value = Column(String(100), default="", comment="指标数值(经济数据类)")
    detail_fetch_status = Column(String(20), default="pending", comment="详情爬取状态: pending/list_only/partial/complete/failed")
    detail_fetch_error = Column(String(500), default="", comment="详情爬取失败原因")
    detail_strategy = Column(String(50), default="", comment="详情抓取策略")
    detail_score = Column(Integer, default=0, comment="详情完整度得分")
    detail_content_length = Column(Integer, default=0, comment="详情正文长度")
    detail_fetched_at = Column(DateTime, comment="详情抓取完成时间")
    is_deleted = Column(Integer, default=0, comment="逻辑删除 0-正常 1-删除")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    channel = relationship("Channel", back_populates="infos", lazy="joined")
    category = relationship("Category", back_populates="infos", lazy="joined")

    __table_args__ = (
        UniqueConstraint("source_id", "channel_id", name="uq_source_channel"),
        Index("idx_category_id", "category_id"),
        Index("idx_channel_id", "channel_id"),
        Index("idx_event_time", "event_time"),
        Index("idx_created_at", "created_at"),
        Index("idx_detail_fetch_status", "detail_fetch_status"),
    )

    def __repr__(self):
        return f"<Info(id={self.id}, title='{self.title[:20]}...')>"

    def to_dict(self):
        """将信息记录转换为字典，用于API返回"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "channel_id": self.channel_id,
            "channel_name": self.channel.name if self.channel else "",
            "source_id": self.source_id,
            "source_url": self.source_url,
            "event_time": self.event_time.strftime("%Y-%m-%d %H:%M:%S") if self.event_time else None,
            "core_entity": self.core_entity,
            "location": self.location,
            "indicator_name": self.indicator_name,
            "indicator_value": self.indicator_value,
            "detail_fetch_status": self.detail_fetch_status,
            "detail_fetch_error": self.detail_fetch_error,
            "detail_strategy": self.detail_strategy,
            "detail_score": self.detail_score,
            "detail_content_length": self.detail_content_length,
            "detail_fetched_at": self.detail_fetched_at.strftime("%Y-%m-%d %H:%M:%S") if self.detail_fetched_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


class InfoAcquisitionLog(Base):
    """信息详情采集执行日志。"""

    __tablename__ = "info_acquisition_log"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="采集日志ID")
    info_id = Column(Integer, ForeignKey("info.id"), nullable=False, comment="信息ID")
    channel_code = Column(String(50), default="", nullable=False, comment="渠道编码")
    strategy = Column(String(50), default="", nullable=False, comment="详情策略")
    status = Column(String(20), default="", nullable=False, comment="详情结果状态")
    score = Column(Integer, default=0, comment="完整度得分")
    content_length = Column(Integer, default=0, comment="正文长度")
    failure_reason = Column(String(255), default="", comment="失败原因")
    matched_rules = Column(String(500), default="", comment="命中规则")
    raw_excerpt = Column(Text, default="", comment="内容摘要")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_info_acquisition_info_created", "info_id", "created_at"),
        Index("idx_info_acquisition_channel_strategy", "channel_code", "strategy"),
    )


class Event(Base):
    """事件主表：面向前端输出的事件对象。"""

    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="事件ID")
    title = Column(String(200), nullable=False, comment="事件标题")
    one_line_summary = Column(String(255), default="", comment="一句话看懂")
    primary_category_id = Column(Integer, ForeignKey("category.id"), nullable=False, comment="主分类ID")
    status = Column(String(20), default="active", comment="事件状态")
    heat_score = Column(Integer, default=0, comment="热度分")
    freshness_score = Column(Integer, default=0, comment="时效分")
    composite_score = Column(Integer, default=0, comment="综合分")
    source_count = Column(Integer, default=0, comment="来源数")
    started_at = Column(DateTime, comment="事件开始时间")
    last_updated_at = Column(DateTime, comment="事件最后更新时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    category = relationship("Category", lazy="joined")

    __table_args__ = (
        Index("idx_event_category_score", "primary_category_id", "composite_score", "last_updated_at"),
        Index("idx_event_status_updated", "status", "last_updated_at"),
    )


class EventItemLink(Base):
    """事件与内容项的关联表。"""

    __tablename__ = "event_item_link"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="关联ID")
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False, comment="事件ID")
    item_id = Column(Integer, ForeignKey("info.id"), nullable=False, comment="内容项ID")
    role = Column(String(20), default="media", comment="内容角色")
    is_primary = Column(Integer, default=0, comment="是否主来源")
    weight = Column(Integer, default=0, comment="权重")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        UniqueConstraint("event_id", "item_id", name="uq_event_item"),
        Index("idx_event_item_item_id", "item_id"),
    )


class EventTimelineEntry(Base):
    """事件时间线节点表。"""

    __tablename__ = "event_timeline_entry"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="时间线节点ID")
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False, comment="事件ID")
    occurred_at = Column(DateTime, nullable=False, comment="发生时间")
    summary = Column(String(255), nullable=False, comment="节点摘要")
    source_item_id = Column(Integer, ForeignKey("info.id"), nullable=False, comment="来源内容项ID")
    confidence = Column(Float, default=0.0, comment="置信度")
    display_order = Column(Integer, default=0, comment="展示顺序")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_event_timeline_event_time", "event_id", "occurred_at"),
    )


class EventSummarySnapshot(Base):
    """事件摘要快照表，用于保存不同类型的摘要。"""

    __tablename__ = "event_summary_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="摘要快照ID")
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False, comment="事件ID")
    summary_type = Column(String(30), nullable=False, comment="摘要类型")
    content = Column(Text, default="", comment="摘要内容")
    version = Column(Integer, default=1, comment="版本号")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_event_summary_lookup", "event_id", "summary_type", "version"),
    )

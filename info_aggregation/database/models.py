"""
信息聚合系统 - 数据库模型定义
使用SQLAlchemy ORM定义渠道表、分类表、信息主表
"""
from datetime import date, datetime
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, DateTime, ForeignKey, Float, Index, UniqueConstraint, JSON
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
    base_interval_minutes = Column(Integer, default=60, comment="基础采集间隔(分钟)，由管理后台配置")
    hot_interval_minutes = Column(Integer, default=10, comment="热点加速采集间隔(分钟)")
    min_interval_minutes = Column(Integer, default=3, comment="允许的最小采集间隔(分钟)")
    max_interval_minutes = Column(Integer, default=240, comment="失败退避后的最大采集间隔(分钟)")
    manual_interval_enabled = Column(Integer, default=1, comment="是否启用人工配置间隔 1-启用 0-禁用")
    effective_interval_minutes = Column(Integer, default=60, comment="当前实际生效采集间隔(分钟)")
    schedule_version = Column(Integer, default=1, comment="调度配置版本，用于调度器热更新")
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
            "base_interval_minutes": self.base_interval_minutes,
            "hot_interval_minutes": self.hot_interval_minutes,
            "min_interval_minutes": self.min_interval_minutes,
            "max_interval_minutes": self.max_interval_minutes,
            "manual_interval_enabled": self.manual_interval_enabled,
            "effective_interval_minutes": self.effective_interval_minutes,
            "schedule_version": self.schedule_version,
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
    tech_topic_type = Column(String(50), default="", comment="科技主题类型")
    tech_entities = Column(String(500), default="", comment="科技核心实体，使用逗号分隔")
    tech_keywords = Column(String(500), default="", comment="科技关键词，使用逗号分隔")
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
        def split_csv(raw_value: str) -> list[str]:
            if not raw_value:
                return []
            return [item.strip() for item in raw_value.split(",") if item.strip()]

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
            "tech_topic_type": self.tech_topic_type,
            "tech_entities": split_csv(self.tech_entities),
            "tech_keywords": split_csv(self.tech_keywords),
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


class DetailJob(Base):
    """详情补偿任务表：保存低分、失败或列表态内容的二次抓取任务。"""

    __tablename__ = "detail_job"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="详情补偿任务ID")
    info_id = Column(Integer, ForeignKey("info.id"), nullable=False, comment="信息ID")
    channel_code = Column(String(50), default="", nullable=False, comment="渠道编码")
    status = Column(String(20), default="pending", nullable=False, comment="任务状态: pending/running/succeeded/failed/cancelled")
    priority = Column(Integer, default=50, comment="任务优先级，数值越大越优先")
    attempt_count = Column(Integer, default=0, comment="已尝试次数")
    max_attempts = Column(Integer, default=3, comment="最大尝试次数")
    next_run_at = Column(DateTime, default=datetime.now, comment="下次可执行时间")
    last_failure_reason = Column(String(255), default="", comment="最近失败原因")
    strategy_hint = Column(String(100), default="", comment="建议使用的详情策略")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    info = relationship("Info", lazy="joined")

    __table_args__ = (
        Index("idx_detail_job_info_status", "info_id", "status"),
        Index("idx_detail_job_status_priority", "status", "priority", "next_run_at"),
        Index("idx_detail_job_channel_status", "channel_code", "status"),
    )


class Event(Base):
    """事件主表：面向前端输出的事件对象。"""

    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="事件ID")
    event_key = Column(String(120), nullable=True, comment="事件稳定键：用于重建时识别同一热点事件")
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
        UniqueConstraint("event_key", name="uk_event_key"),
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


class EventAnalysisRun(Base):
    """事件分析运行表：记录规则或大模型分析的一次完整执行。"""

    __tablename__ = "event_analysis_run"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="事件分析运行ID")
    event_id = Column(Integer, nullable=False, comment="事件ID，由代码约束关联event.id")
    analysis_version = Column(String(30), default="v1", nullable=False, comment="分析版本")
    mode = Column(String(30), default="rule", nullable=False, comment="分析模式: rule/hybrid/llm")
    provider = Column(String(50), default="rule", nullable=False, comment="分析提供方")
    model_name = Column(String(100), default="", comment="模型名称")
    status = Column(String(20), default="succeeded", nullable=False, comment="运行状态")
    input_item_count = Column(Integer, default=0, comment="输入来源数量")
    quality_score = Column(Float, default=0.0, comment="分析质量分")
    confidence = Column(Float, default=0.0, comment="分析置信度")
    fallback_used = Column(Integer, default=0, comment="是否使用规则回退")
    failure_reason = Column(String(500), default="", comment="失败原因")
    started_at = Column(DateTime, default=datetime.now, comment="开始时间")
    finished_at = Column(DateTime, comment="结束时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_event_analysis_run_event_time", "event_id", "created_at"),
        Index("idx_event_analysis_run_status", "status", "provider"),
    )


class EventFactSnapshot(Base):
    """事件事实快照表：保存从来源中抽取的关键事实和证据。"""

    __tablename__ = "event_fact_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="事件事实ID")
    event_id = Column(Integer, nullable=False, comment="事件ID，由代码约束关联event.id")
    run_id = Column(Integer, nullable=False, comment="分析运行ID，由代码约束关联event_analysis_run.id")
    fact_type = Column(String(50), nullable=False, comment="事实类型")
    content = Column(Text, default="", comment="事实内容")
    source_item_id = Column(Integer, comment="来源内容ID，由代码约束关联info.id")
    confidence = Column(Float, default=0.0, comment="事实置信度")
    evidence = Column(JSON, comment="证据JSON")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_event_fact_event_type", "event_id", "fact_type"),
        Index("idx_event_fact_run", "run_id"),
    )


class EventAnalysisSnapshot(Base):
    """事件分析快照表：保存结构化分析输出。"""

    __tablename__ = "event_analysis_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="事件分析快照ID")
    event_id = Column(Integer, nullable=False, comment="事件ID，由代码约束关联event.id")
    run_id = Column(Integer, nullable=False, comment="分析运行ID，由代码约束关联event_analysis_run.id")
    analysis_type = Column(String(50), nullable=False, comment="分析类型")
    content = Column(Text, default="", comment="分析内容")
    provider = Column(String(50), default="rule", nullable=False, comment="分析提供方")
    model_name = Column(String(100), default="", comment="模型名称")
    quality_score = Column(Float, default=0.0, comment="质量分")
    confidence = Column(Float, default=0.0, comment="置信度")
    version = Column(Integer, default=1, comment="版本号")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_event_analysis_snapshot_lookup", "event_id", "analysis_type", "version"),
        Index("idx_event_analysis_snapshot_run", "run_id"),
    )


class EventTimelineAnalysis(Base):
    """事件时间线分析表：保存升级后的时间线节点。"""

    __tablename__ = "event_timeline_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="事件时间线分析ID")
    event_id = Column(Integer, nullable=False, comment="事件ID，由代码约束关联event.id")
    run_id = Column(Integer, nullable=False, comment="分析运行ID，由代码约束关联event_analysis_run.id")
    occurred_at = Column(DateTime, nullable=False, comment="节点发生时间")
    summary = Column(String(255), nullable=False, comment="节点摘要")
    source_item_id = Column(Integer, comment="来源内容ID，由代码约束关联info.id")
    confidence = Column(Float, default=0.0, comment="节点置信度")
    evidence = Column(JSON, comment="证据JSON")
    display_order = Column(Integer, default=0, comment="展示顺序")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_event_timeline_analysis_event_time", "event_id", "occurred_at"),
        Index("idx_event_timeline_analysis_run", "run_id"),
    )


class LLMModelConfig(Base):
    """大模型配置表：支持管理端维护多个事件分析模型。"""

    __tablename__ = "llm_model_config"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="大模型配置ID")
    provider_name = Column(String(50), nullable=False, comment="模型供应商名称")
    provider_code = Column(String(50), nullable=False, comment="模型供应商编码")
    base_url = Column(String(255), default="", nullable=False, comment="OpenAI兼容接口地址")
    api_key = Column(String(500), default="", comment="API密钥")
    model_name = Column(String(100), default="", nullable=False, comment="模型名称")
    is_enabled = Column(Integer, default=0, nullable=False, comment="是否启用: 1启用 0停用")
    daily_call_limit = Column(Integer, default=0, nullable=False, comment="每日调用上限，0表示不限")
    daily_call_count = Column(Integer, default=0, nullable=False, comment="当日已调用次数")
    last_call_date = Column(Date, default=date.today, comment="最近调用日期")
    priority = Column(Integer, default=100, nullable=False, comment="选择优先级，数值越小越优先")
    consecutive_failure_count = Column(Integer, default=0, nullable=False, comment="连续失败次数，用于自动熔断")
    circuit_open_until = Column(DateTime, comment="熔断结束时间，未到期前跳过该模型")
    last_failure_reason = Column(String(500), default="", comment="最近失败原因")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    __table_args__ = (
        UniqueConstraint("provider_code", "model_name", name="uq_llm_provider_model"),
        Index("idx_llm_enabled_priority", "is_enabled", "priority", "id"),
        Index("idx_llm_circuit_open_until", "circuit_open_until"),
    )


class LLMCallLog(Base):
    """大模型调用日志表：记录事件分析模型调用的成功、失败和耗时。"""

    __tablename__ = "llm_call_log"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="大模型调用日志ID")
    config_id = Column(Integer, nullable=False, comment="大模型配置ID，由代码约束关联llm_model_config.id")
    provider_code = Column(String(50), nullable=False, comment="供应商编码")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    status = Column(String(20), nullable=False, comment="调用状态: succeeded/failed")
    latency_ms = Column(Integer, default=0, nullable=False, comment="调用耗时毫秒")
    input_item_count = Column(Integer, default=0, nullable=False, comment="输入来源数量")
    error_message = Column(String(500), default="", comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_llm_call_config_time", "config_id", "created_at"),
        Index("idx_llm_call_status_time", "status", "created_at"),
    )


class CrawlTask(Base):
    """采集任务表：保存可调度的数据采集任务。"""

    __tablename__ = "crawl_task"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="采集任务ID")
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False, comment="渠道ID")
    task_code = Column(String(80), nullable=False, unique=True, comment="任务编码")
    task_name = Column(String(100), nullable=False, comment="任务名称")
    schedule_type = Column(String(20), default="interval", nullable=False, comment="调度类型")
    schedule_value = Column(String(100), default="", nullable=False, comment="调度配置值")
    schedule_version = Column(Integer, default=0, nullable=False, comment="已同步的调度配置版本")
    status = Column(String(20), default="active", nullable=False, comment="任务状态")
    last_run_at = Column(DateTime, comment="最近运行时间")
    next_run_at = Column(DateTime, comment="下次计划运行时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    channel = relationship("Channel", lazy="joined")

    __table_args__ = (
        Index("idx_crawl_task_channel_status", "channel_id", "status"),
    )


class CrawlRunLog(Base):
    """采集运行日志表：记录每次采集执行结果。"""

    __tablename__ = "crawl_run_log"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="采集运行日志ID")
    task_id = Column(Integer, ForeignKey("crawl_task.id"), comment="采集任务ID")
    channel_code = Column(String(50), nullable=False, comment="渠道编码")
    trigger_type = Column(String(20), default="scheduler", nullable=False, comment="触发方式")
    status = Column(String(20), nullable=False, comment="运行状态")
    raw_count = Column(Integer, default=0, comment="原始抓取数量")
    cleaned_count = Column(Integer, default=0, comment="清洗后数量")
    saved_count = Column(Integer, default=0, comment="入库数量")
    detail_success_count = Column(Integer, default=0, comment="详情成功数量")
    detail_failed_count = Column(Integer, default=0, comment="详情失败数量")
    error_message = Column(String(1000), default="", comment="错误信息")
    started_at = Column(DateTime, nullable=False, comment="开始时间")
    finished_at = Column(DateTime, comment="结束时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    task = relationship("CrawlTask", lazy="joined")

    __table_args__ = (
        Index("idx_crawl_run_channel_time", "channel_code", "started_at"),
        Index("idx_crawl_run_task_time", "task_id", "started_at"),
    )


class CrawlHealthSnapshot(Base):
    """采集健康快照表：保存渠道采集稳定性指标。"""

    __tablename__ = "crawl_health_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="采集健康快照ID")
    channel_code = Column(String(50), nullable=False, comment="渠道编码")
    success_rate = Column(Float, default=0.0, comment="最近采集成功率")
    detail_complete_rate = Column(Float, default=0.0, comment="详情完整率")
    avg_detail_score = Column(Float, default=0.0, comment="平均详情质量分")
    last_success_at = Column(DateTime, comment="最近成功时间")
    last_failed_at = Column(DateTime, comment="最近失败时间")
    snapshot_at = Column(DateTime, default=datetime.now, comment="快照时间")

    __table_args__ = (
        Index("idx_crawl_health_channel_time", "channel_code", "snapshot_at"),
    )


class DataQualitySnapshot(Base):
    """数据质量快照表：保存重复、缺失、低质量等治理指标。"""

    __tablename__ = "data_quality_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="质量快照ID")
    category_code = Column(String(50), default="all", nullable=False, comment="分类编码")
    total_count = Column(Integer, default=0, comment="总内容数量")
    duplicate_title_count = Column(Integer, default=0, comment="重复标题数量")
    empty_content_count = Column(Integer, default=0, comment="正文为空数量")
    low_detail_score_count = Column(Integer, default=0, comment="低详情评分数量")
    missing_entity_count = Column(Integer, default=0, comment="核心实体缺失数量")
    snapshot_payload = Column(JSON, comment="完整质量报告JSON")
    snapshot_at = Column(DateTime, default=datetime.now, comment="快照时间")

    __table_args__ = (
        Index("idx_data_quality_category_time", "category_code", "snapshot_at"),
    )

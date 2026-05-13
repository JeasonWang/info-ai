"""
信息聚合系统 - 数据库会话管理
提供数据库连接、会话管理、初始化功能
"""
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session

from config import SQLALCHEMY_DATABASE_URL
from .models import Base

logger = logging.getLogger(__name__)

engine = None
SessionFactory = None
Session = None


def configure_engine(database_url: str):
    """Rebuild SQLAlchemy engine/session bindings for the given database URL."""
    global engine, SessionFactory, Session
    engine = create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    )
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Session = scoped_session(SessionFactory)


configure_engine(SQLALCHEMY_DATABASE_URL)


def get_session():
    """
    获取数据库会话
    返回: SQLAlchemy Session实例
    """
    session = Session()
    try:
        return session
    except Exception:
        session.rollback()
        raise


def init_db():
    """
    初始化数据库：创建所有表结构
    """
    logger.info("正在初始化数据库，创建表结构...")
    Base.metadata.create_all(bind=engine)
    _ensure_event_key_column()
    _ensure_llm_call_log_payload_columns()
    logger.info("数据库表结构创建完成")


def _ensure_event_key_column():
    """兼容旧库：为事件表补充稳定键字段，避免重建事件时丢失用户关系。"""

    inspector = inspect(engine)
    if "event" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("event")}
    if "event_key" in columns:
        return

    dialect_name = engine.dialect.name
    column_sql = "VARCHAR(120) NULL"
    if dialect_name == "mysql":
        alter_sql = (
            "ALTER TABLE event ADD COLUMN event_key "
            f"{column_sql} COMMENT '事件稳定键：用于重建时识别同一热点事件' AFTER id"
        )
    else:
        alter_sql = f"ALTER TABLE event ADD COLUMN event_key {column_sql}"

    with engine.begin() as connection:
        connection.execute(text(alter_sql))
        if dialect_name == "mysql":
            connection.execute(text("UPDATE event SET event_key = CONCAT('legacy-', id) WHERE event_key IS NULL"))
        else:
            connection.execute(text("UPDATE event SET event_key = 'legacy-' || id WHERE event_key IS NULL"))


def _ensure_llm_call_log_payload_columns():
    """兼容旧库：为大模型调用日志补充请求和响应内容字段。"""

    inspector = inspect(engine)
    if "llm_call_log" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("llm_call_log")}
    dialect_name = engine.dialect.name
    column_defs = {
        "request_payload": "JSON NULL" if dialect_name == "mysql" else "JSON NULL",
        "response_content": "LONGTEXT NULL" if dialect_name == "mysql" else "TEXT NULL",
        "response_payload": "JSON NULL" if dialect_name == "mysql" else "JSON NULL",
    }
    comments = {
        "request_payload": "请求参数快照，包含消息内容",
        "response_content": "模型返回文本",
        "response_payload": "模型原始响应快照",
    }
    with engine.begin() as connection:
        for column_name, column_sql in column_defs.items():
            if column_name in columns:
                continue
            if dialect_name == "mysql":
                sql = f"ALTER TABLE llm_call_log ADD COLUMN {column_name} {column_sql} COMMENT '{comments[column_name]}'"
            else:
                sql = f"ALTER TABLE llm_call_log ADD COLUMN {column_name} {column_sql}"
            connection.execute(text(sql))

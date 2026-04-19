"""
信息聚合系统 - 数据库会话管理
提供数据库连接、会话管理、初始化功能
"""
import logging
from sqlalchemy import create_engine
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
    logger.info("数据库表结构创建完成")

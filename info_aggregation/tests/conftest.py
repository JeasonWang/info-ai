import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("ENABLE_PUBLIC_API", "1")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import configure_engine, get_session, init_db  # noqa: E402
from services.collection.credential_provider import CredentialProvider  # noqa: E402


@pytest.fixture(autouse=True)
def reset_credential_provider_singleton():
    """隔离测试间的凭证单例状态，避免数据库凭证缓存影响 env 兼容测试。"""
    CredentialProvider._instance = None
    yield
    CredentialProvider._instance = None


@pytest.fixture()
def session(tmp_path):
    db_path = tmp_path / "event-models.db"
    configure_engine(f"sqlite:///{db_path}")
    init_db()
    session = get_session()
    try:
        yield session
    finally:
        session.close()

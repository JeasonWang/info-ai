import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import configure_engine, get_session, init_db  # noqa: E402


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

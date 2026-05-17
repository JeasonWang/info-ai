"""Read business config from database system_config table, with .env fallback."""

from database import get_session, SystemConfig
import os, logging

logger = logging.getLogger(__name__)

_cache: dict[str, str] = {}
_CACHE_MAX_AGE_SECONDS = 300  # 5 min cache
_cache_ts: float = 0


def _refresh_cache():
    """Refresh config cache from database."""
    global _cache, _cache_ts
    import time
    now = time.time()
    if _cache and (now - _cache_ts) < _CACHE_MAX_AGE_SECONDS:
        return
    try:
        session = get_session()
        try:
            rows = session.query(SystemConfig).all()
            _cache = {row.config_key: row.config_value for row in rows}
            _cache_ts = now
        finally:
            session.close()
    except Exception:
        logger.warning("Failed to load system_config from DB, using .env fallback")


def get_config(key: str, fallback: str | None = None) -> str | None:
    """Get a config value. DB first, .env fallback."""
    _refresh_cache()
    if key in _cache:
        return _cache[key]
    return os.environ.get(key, fallback)


def get_config_bool(key: str, fallback: bool = False) -> bool:
    val = get_config(key)
    if val is None:
        return fallback
    return val.lower() in ("1", "true", "yes")


def get_config_int(key: str, fallback: int = 0) -> int:
    val = get_config(key)
    if val is None:
        return fallback
    try:
        return int(val)
    except ValueError:
        return fallback


def get_config_float(key: str, fallback: float = 0.0) -> float:
    val = get_config(key)
    if val is None:
        return fallback
    try:
        return float(val)
    except ValueError:
        return fallback
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import database.session as db_session
from config import EVENT_ANALYSIS_LLM_COOLDOWN_MINUTES, EVENT_ANALYSIS_LLM_FAILURE_THRESHOLD
from database import LLMCallLog, LLMModelConfig
from sqlalchemy import text


MASK_PLACEHOLDERS = {"", "******", "********"}


@dataclass(frozen=True)
class LLMModelConfigSnapshot:
    id: int
    provider_name: str
    provider_code: str
    base_url: str
    api_key: str
    model_name: str
    is_enabled: int
    daily_call_limit: int
    daily_call_count: int
    last_call_date: date | None
    priority: int
    consecutive_failure_count: int
    circuit_open_until: datetime | None
    last_failure_reason: str


def _snapshot(config: LLMModelConfig) -> LLMModelConfigSnapshot:
    return LLMModelConfigSnapshot(
        id=config.id,
        provider_name=config.provider_name or "",
        provider_code=config.provider_code or "",
        base_url=config.base_url or "",
        api_key=config.api_key or "",
        model_name=config.model_name or "",
        is_enabled=int(config.is_enabled or 0),
        daily_call_limit=int(config.daily_call_limit or 0),
        daily_call_count=int(config.daily_call_count or 0),
        last_call_date=config.last_call_date,
        priority=int(config.priority or 100),
        consecutive_failure_count=int(config.consecutive_failure_count or 0),
        circuit_open_until=config.circuit_open_until,
        last_failure_reason=config.last_failure_reason or "",
    )


def _mask_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"


def _to_dict(config: LLMModelConfig, mask_secret: bool = True) -> dict:
    recent_logs = getattr(config, "_recent_call_stats", None) or {}
    return {
        "id": config.id,
        "provider_name": config.provider_name,
        "provider_code": config.provider_code,
        "base_url": config.base_url,
        "api_key": _mask_api_key(config.api_key or "") if mask_secret else config.api_key or "",
        "model_name": config.model_name,
        "is_enabled": config.is_enabled,
        "daily_call_limit": config.daily_call_limit,
        "daily_call_count": config.daily_call_count,
        "last_call_date": config.last_call_date.isoformat() if config.last_call_date else "",
        "priority": config.priority,
        "consecutive_failure_count": config.consecutive_failure_count or 0,
        "circuit_open_until": config.circuit_open_until.strftime("%Y-%m-%d %H:%M:%S") if config.circuit_open_until else "",
        "last_failure_reason": config.last_failure_reason or "",
        "success_count": recent_logs.get("success_count", 0),
        "failure_count": recent_logs.get("failure_count", 0),
        "avg_latency_ms": recent_logs.get("avg_latency_ms", 0),
        "last_error_message": recent_logs.get("last_error_message", ""),
        "created_at": config.created_at.strftime("%Y-%m-%d %H:%M:%S") if config.created_at else "",
        "updated_at": config.updated_at.strftime("%Y-%m-%d %H:%M:%S") if config.updated_at else "",
    }


def list_llm_model_configs(session) -> list[dict]:
    configs = session.query(LLMModelConfig).order_by(LLMModelConfig.priority.asc(), LLMModelConfig.id.asc()).all()
    for config in configs:
        logs = (
            session.query(LLMCallLog)
            .filter(LLMCallLog.config_id == config.id)
            .order_by(LLMCallLog.created_at.desc(), LLMCallLog.id.desc())
            .limit(100)
            .all()
        )
        success_logs = [log for log in logs if log.status == "succeeded"]
        failed_logs = [log for log in logs if log.status == "failed"]
        latency_logs = [log.latency_ms or 0 for log in logs if (log.latency_ms or 0) >= 0]
        last_failed = next((log for log in logs if log.status == "failed" and log.error_message), None)
        config._recent_call_stats = {
            "success_count": len(success_logs),
            "failure_count": len(failed_logs),
            "avg_latency_ms": round(sum(latency_logs) / len(latency_logs)) if latency_logs else 0,
            "last_error_message": last_failed.error_message if last_failed else "",
        }
    return [_to_dict(config) for config in configs]


def _apply_payload(config: LLMModelConfig, payload: dict, preserve_empty_secret: bool = False):
    for field in [
        "provider_name",
        "provider_code",
        "base_url",
        "model_name",
        "is_enabled",
        "daily_call_limit",
        "daily_call_count",
        "priority",
        "consecutive_failure_count",
    ]:
        if field in payload and payload[field] is not None:
            setattr(config, field, payload[field])
    if "api_key" in payload and payload["api_key"] not in MASK_PLACEHOLDERS:
        config.api_key = payload["api_key"]
    elif "api_key" in payload and not preserve_empty_secret:
        config.api_key = payload["api_key"] or ""


def create_llm_model_config(session, payload: dict) -> LLMModelConfig:
    config = LLMModelConfig(
        provider_name=(payload.get("provider_name") or "").strip(),
        provider_code=(payload.get("provider_code") or "").strip(),
        base_url=(payload.get("base_url") or "").strip(),
        model_name=(payload.get("model_name") or "").strip(),
        api_key=payload.get("api_key") or "",
        is_enabled=int(payload.get("is_enabled") or 0),
        daily_call_limit=int(payload.get("daily_call_limit") or 0),
        daily_call_count=int(payload.get("daily_call_count") or 0),
        priority=int(payload.get("priority") or 100),
        consecutive_failure_count=0,
        circuit_open_until=None,
        last_failure_reason="",
        last_call_date=date.today(),
    )
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def update_llm_model_config(session, config_id: int, payload: dict) -> LLMModelConfig | None:
    config = session.get(LLMModelConfig, config_id)
    if not config:
        return None
    _apply_payload(config, payload, preserve_empty_secret=True)
    session.commit()
    session.refresh(config)
    return config


def select_available_llm_config(session) -> LLMModelConfig | None:
    configs = (
        session.query(LLMModelConfig)
        .filter(LLMModelConfig.is_enabled == 1)
        .order_by(LLMModelConfig.priority.asc(), LLMModelConfig.id.asc())
        .populate_existing()
        .all()
    )
    today = date.today()
    now = datetime.now()
    for config in configs:
        if config.circuit_open_until and config.circuit_open_until > now:
            continue
        limit = config.daily_call_limit or 0
        effective_count = 0 if config.last_call_date != today else (config.daily_call_count or 0)
        if limit > 0 and effective_count >= limit:
            continue
        return config
    return None


def select_available_llm_config_snapshot(session) -> LLMModelConfigSnapshot | None:
    config = select_available_llm_config(session)
    if config is None:
        return None
    return _snapshot(config)


def get_llm_config_snapshot(session, config_id: int, require_enabled: bool = False) -> LLMModelConfigSnapshot | None:
    config = session.get(LLMModelConfig, config_id)
    if config is None:
        return None
    if require_enabled and int(config.is_enabled or 0) != 1:
        return None
    return _snapshot(config)


def increment_llm_call_count(session, config: LLMModelConfig):
    today = date.today()
    if config.last_call_date != today:
        config.daily_call_count = 0
        config.last_call_date = today
    config.daily_call_count = (config.daily_call_count or 0) + 1
    session.flush()


def _record_llm_call_log(
    session,
    config: LLMModelConfig,
    status: str,
    latency_ms: int,
    input_item_count: int,
    error_message: str = "",
    request_payload: dict | None = None,
    response_content: str = "",
    response_payload: dict | None = None,
) -> LLMCallLog:
    log = LLMCallLog(
        config_id=config.id,
        provider_code=config.provider_code,
        model_name=config.model_name,
        status=status,
        latency_ms=max(0, int(latency_ms)),
        input_item_count=input_item_count,
        request_payload=request_payload,
        response_content=response_content or "",
        response_payload=response_payload,
        error_message=(error_message or "")[:500],
    )
    session.add(log)
    session.flush()
    return log


def record_llm_call_success(
    session,
    config: LLMModelConfig,
    latency_ms: int,
    input_item_count: int,
    request_payload: dict | None = None,
    response_content: str = "",
    response_payload: dict | None = None,
) -> LLMCallLog:
    increment_llm_call_count(session, config)
    config.consecutive_failure_count = 0
    config.circuit_open_until = None
    config.last_failure_reason = ""
    log = _record_llm_call_log(
        session,
        config,
        "succeeded",
        latency_ms,
        input_item_count,
        request_payload=request_payload,
        response_content=response_content,
        response_payload=response_payload,
    )
    session.flush()
    return log


def _set_short_lock_wait(session, seconds: int = 3):
    bind = session.get_bind()
    if getattr(bind.dialect, "name", "") == "mysql":
        session.execute(text("SET SESSION innodb_lock_wait_timeout = :seconds"), {"seconds": seconds})


def _new_session():
    if db_session.SessionFactory is None:
        raise RuntimeError("database session factory is not configured")
    return db_session.SessionFactory()


def select_available_llm_config_independent() -> LLMModelConfigSnapshot | None:
    session = _new_session()
    try:
        return select_available_llm_config_snapshot(session)
    finally:
        session.close()


def get_llm_config_snapshot_independent(config_id: int, require_enabled: bool = False) -> LLMModelConfigSnapshot | None:
    session = _new_session()
    try:
        return get_llm_config_snapshot(session, config_id, require_enabled=require_enabled)
    finally:
        session.close()


def record_llm_call_success_independent(
    config_id: int,
    latency_ms: int,
    input_item_count: int,
    request_payload: dict | None = None,
    response_content: str = "",
    response_payload: dict | None = None,
) -> None:
    session = _new_session()
    try:
        _set_short_lock_wait(session)
        config = session.get(LLMModelConfig, config_id)
        if config is None:
            return
        record_llm_call_success(
            session,
            config,
            latency_ms,
            input_item_count,
            request_payload=request_payload,
            response_content=response_content,
            response_payload=response_payload,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def record_llm_call_failure(
    session,
    config: LLMModelConfig,
    latency_ms: int,
    input_item_count: int,
    error_message: str,
    request_payload: dict | None = None,
    response_content: str = "",
    response_payload: dict | None = None,
) -> LLMCallLog:
    increment_llm_call_count(session, config)
    config.consecutive_failure_count = (config.consecutive_failure_count or 0) + 1
    config.last_failure_reason = (error_message or "")[:500]
    if config.consecutive_failure_count >= EVENT_ANALYSIS_LLM_FAILURE_THRESHOLD:
        config.circuit_open_until = datetime.now() + timedelta(minutes=EVENT_ANALYSIS_LLM_COOLDOWN_MINUTES)
    log = _record_llm_call_log(
        session,
        config,
        "failed",
        latency_ms,
        input_item_count,
        error_message,
        request_payload=request_payload,
        response_content=response_content,
        response_payload=response_payload,
    )
    session.flush()
    return log


def record_llm_call_failure_independent(
    config_id: int,
    latency_ms: int,
    input_item_count: int,
    error_message: str,
    request_payload: dict | None = None,
    response_content: str = "",
    response_payload: dict | None = None,
) -> None:
    session = _new_session()
    try:
        _set_short_lock_wait(session)
        config = session.get(LLMModelConfig, config_id)
        if config is None:
            return
        record_llm_call_failure(
            session,
            config,
            latency_ms,
            input_item_count,
            error_message,
            request_payload=request_payload,
            response_content=response_content,
            response_payload=response_payload,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

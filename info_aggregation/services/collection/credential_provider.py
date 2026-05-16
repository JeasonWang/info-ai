import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import os

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CredentialSpec:
    """单个采集凭证的配置说明。"""

    name: str
    required: bool = False


@dataclass(frozen=True)
class CredentialStatus:
    """脱敏后的凭证状态，用于管理端健康检查。"""

    name: str
    configured: bool
    source: str
    required: bool
    length: int
    preview: str
    health: str
    verified_at: Optional[str] = None


@dataclass(frozen=True)
class ChannelCredentialInfo:
    """渠道凭证信息（管理端使用）。"""

    channel_code: str
    cookie_configured: bool
    cookie_preview: str
    cookie_status: str  # active / expired / invalid / not_configured
    extra_credentials: dict
    updated_at: Optional[str]
    updated_by: str


@dataclass(frozen=True)
class _DatabaseCredentialRead:
    found: bool
    value: str = ""
    channel_code: str = ""
    credential_key: str = ""
    status: str = ""
    source: str = "database"


CHANNEL_CREDENTIAL_SPECS: dict[str, tuple[CredentialSpec, ...]] = {
    "weibo": (CredentialSpec("WEIBO_COOKIE", required=True),),
    "zhihu": (
        CredentialSpec("ZHIHU_COOKIE", required=True),
        CredentialSpec("ZHIHU_ZSE_93", required=False),
        CredentialSpec("ZHIHU_ZSE_96", required=False),
    ),
    "xiaohongshu": (CredentialSpec("XHS_COOKIE", required=True),),
}


ENV_VAR_TO_CHANNEL_CREDENTIAL: dict[str, tuple[str, str]] = {
    # env_var_name -> (channel_code, credential_key)
    "WEIBO_COOKIE": ("weibo", "cookie"),
    "ZHIHU_COOKIE": ("zhihu", "cookie"),
    "ZHIHU_ZSE_93": ("zhihu", "zse_93"),
    "ZHIHU_ZSE_96": ("zhihu", "zse_96"),
    "XHS_COOKIE": ("xiaohongshu", "cookie"),
}


def _strip_env_quotes(value: str) -> str:
    value = (value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _candidate_env_files() -> list[Path]:
    service_root = Path(__file__).resolve().parents[1]
    repo_root = service_root.parent
    candidates = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        service_root / ".env",
        repo_root / ".env",
    ]
    seen = set()
    unique_candidates = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(path)
    return unique_candidates


class CredentialProvider:
    """
    统一读取采集凭证，支持三层优先级：
    1. 环境变量（最高优先级，用于本地开发覆盖）
    2. .env 文件（用于部署配置）
    3. 数据库 channel 表（用于管理端热更新）

    凭证更新后调用 invalidate_cache() 清除缓存。
    """

    _instance: Optional["CredentialProvider"] = None
    _lock = threading.Lock()

    def __init__(self, env_files: list[Path] | None = None, session_factory=None):
        self.env_files = env_files or _candidate_env_files()
        self._session_factory = session_factory
        self._cache: dict[str, tuple[str, str]] = {}
        self._cache_ttl: dict[str, datetime] = {}
        self._logged_states: set[tuple[str, str, str, int, bool]] = set()
        self._cache_duration_seconds = 30  # 缓存30秒后自动过期

    @classmethod
    def get_instance(cls, session_factory=None) -> "CredentialProvider":
        """获取单例实例，线程安全。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(session_factory=session_factory)
        else:
            cls._instance.env_files = _candidate_env_files()
            if session_factory is not None:
                cls._instance._session_factory = session_factory
        return cls._instance

    @classmethod
    def invalidate_cache(cls) -> None:
        """清除凭证缓存，用于凭证更新后立即生效。"""
        if cls._instance is not None:
            with cls._lock:
                cls._instance._cache.clear()
                cls._instance._cache_ttl.clear()
                cls._instance._logged_states.clear()

    def get(self, name: str) -> str:
        return self.get_with_source(name)[0]

    def get_with_source(self, name: str) -> tuple[str, str]:
        """
        获取凭证值和来源。

        渠道 Cookie 已数据库化：正常服务启动后优先使用数据库凭证。
        环境变量和 .env 仅作为旧脚本、离线调试或数据库不可用时的兼容兜底。
        """
        # 数据库凭证允许短缓存，减少爬虫高频读取造成的数据库压力。
        cached = self._get_cached(name)
        if cached is not None:
            return cached

        db_credential = self._read_db_credential(name)
        if db_credential.found:
            self._log_credential_state(name, db_credential, bool(db_credential.value))
        if db_credential.value:
            result = (db_credential.value, "database")
            self._set_cache(name, result)
            return result
        if db_credential.found:
            return ("", "")

        env_value = os.getenv(name, "").strip()
        if env_value:
            value = _strip_env_quotes(env_value)
            self._log_mapped_credential_state(name, value=value, source="environment", status="legacy")
            return (value, "environment")

        for env_file in self.env_files:
            value = self._read_env_file_value(env_file, name)
            if value:
                self._log_mapped_credential_state(name, value=value, source=f".env:{env_file.name}", status="legacy")
                return (value, f".env:{env_file.name}")

        self._log_mapped_credential_state(name, value="", source="none", status="not_configured")
        return ("", "")

    def get_cookie(self, channel_code: str) -> tuple[str, str]:
        """获取指定渠道的 Cookie，兼容旧接口。"""
        env_map = {
            "weibo": "WEIBO_COOKIE",
            "zhihu": "ZHIHU_COOKIE",
            "xiaohongshu": "XHS_COOKIE",
        }
        env_name = env_map.get(channel_code)
        if env_name:
            return self.get_with_source(env_name)
        return ("", "")

    def get_zse_headers(self, channel_code: str) -> tuple[dict[str, str], str]:
        """获取知乎的 ZSE 头信息。"""
        if channel_code != "zhihu":
            return ({}, "")

        headers = {}
        source = ""

        zse_93, src1 = self.get_with_source("ZHIHU_ZSE_93")
        if zse_93:
            headers["x-zse-93"] = zse_93
            source = src1

        zse_96, src2 = self.get_with_source("ZHIHU_ZSE_96")
        if zse_96:
            headers["x-zse-96"] = zse_96

        return (headers, source)

    def status(self, spec: CredentialSpec) -> CredentialStatus:
        value, source = self.get_with_source(spec.name)
        configured = bool(value)
        cookies_data = self._get_cookies_metadata(spec.name)

        return CredentialStatus(
            name=spec.name,
            configured=configured,
            source=source,
            required=spec.required,
            length=len(value),
            preview=_mask_secret(value),
            health=_credential_health(configured=configured, required=spec.required),
            verified_at=cookies_data.get("last_verified_at") if cookies_data else None,
        )

    def channel_report(self, channel_code: str) -> dict:
        specs = CHANNEL_CREDENTIAL_SPECS.get(channel_code, ())
        statuses = [self.status(spec) for spec in specs]
        missing_required = [status.name for status in statuses if status.required and not status.configured]
        if not specs:
            health = "not_required"
        elif missing_required:
            health = "missing_required"
        else:
            health = "ready"
        return {
            "channel_code": channel_code,
            "health": health,
            "missing_required": missing_required,
            "credentials": [status.__dict__ for status in statuses],
        }

    def all_channel_reports(self, channel_codes: list[str] | None = None) -> dict:
        codes = channel_codes or sorted(CHANNEL_CREDENTIAL_SPECS)
        return {channel_code: self.channel_report(channel_code) for channel_code in codes}

    def get_channel_credential_info(self, channel_code: str) -> Optional[ChannelCredentialInfo]:
        """获取渠道凭证详细信息（用于管理端）。"""
        if not self._session_factory:
            return None

        try:
            from database import get_session, Channel

            with get_session() as session:
                channel = session.query(Channel).filter(Channel.code == channel_code).first()
                if not channel:
                    return None

                cookies_data = None
                if channel.cookies:
                    try:
                        cookies_data = json.loads(channel.cookies) if isinstance(channel.cookies, str) else channel.cookies
                    except json.JSONDecodeError:
                        cookies_data = {"cookie": channel.cookies, "status": "invalid"}

                cookie_value = cookies_data.get("cookie", "") if cookies_data else ""
                cookie_status = cookies_data.get("status", "not_configured") if cookies_data else "not_configured"
                runtime_configured = bool(cookie_value) and not _is_sample_credential_status(cookie_status)
                return ChannelCredentialInfo(
                    channel_code=channel_code,
                    cookie_configured=runtime_configured,
                    cookie_preview=_mask_secret(cookie_value),
                    cookie_status=cookie_status,
                    extra_credentials=channel.extra_credentials or {},
                    updated_at=channel.credentials_updated_at.strftime("%Y-%m-%d %H:%M:%S") if channel.credentials_updated_at else None,
                    updated_by=channel.credentials_updated_by or "",
                )
        except Exception as e:
            logger.error(f"获取渠道凭证信息失败: {e}")
            return None

    def update_channel_credentials(
        self, channel_code: str, cookies: str = None, extra_credentials: dict = None, updated_by: str = ""
    ) -> bool:
        """更新渠道凭证到数据库。"""
        if not self._session_factory:
            logger.error("无法更新凭证：未配置 session_factory")
            return False

        try:
            from database import get_session, Channel

            with get_session() as session:
                channel = session.query(Channel).filter(Channel.code == channel_code).first()
                if not channel:
                    logger.error(f"渠道不存在: {channel_code}")
                    return False

                if cookies is not None:
                    # 解析并更新 cookies 字段
                    try:
                        existing = json.loads(channel.cookies) if channel.cookies else {}
                    except json.JSONDecodeError:
                        existing = {}

                    new_cookie_data = json.loads(cookies) if cookies.startswith("{") else {"cookie": cookies}
                    existing.update(new_cookie_data)
                    # 用户主动保存新 cookie 时，无论旧状态如何，都标记为 active
                    if existing.get("cookie"):
                        existing["status"] = "active"
                    existing.setdefault("last_verified_at", None)
                    channel.cookies = json.dumps(existing, ensure_ascii=False)

                if extra_credentials is not None:
                    if channel_code == "zhihu":
                        zhihu_extra = extra_credentials.get("zhihu") if isinstance(extra_credentials, dict) else None
                        if isinstance(zhihu_extra, dict) and (
                            zhihu_extra.get("zse_93") or zhihu_extra.get("zse_96")
                        ) and _is_sample_credential_status(zhihu_extra.get("status", "")):
                            zhihu_extra["status"] = "active"
                    channel.extra_credentials = extra_credentials

                channel.credentials_updated_at = datetime.now()
                channel.credentials_updated_by = updated_by

                session.commit()

                # 清除缓存使新凭证立即生效
                self.invalidate_cache()

                logger.info(f"渠道凭证已更新: {channel_code}")
                return True

        except Exception as e:
            logger.error(f"更新渠道凭证失败: {e}")
            return False

    def delete_channel_credentials(self, channel_code: str) -> bool:
        """清除渠道凭证。"""
        if not self._session_factory:
            logger.error("无法清除凭证：未配置 session_factory")
            return False

        try:
            from database import get_session, Channel

            with get_session() as session:
                channel = session.query(Channel).filter(Channel.code == channel_code).first()
                if not channel:
                    logger.error(f"渠道不存在: {channel_code}")
                    return False
                channel.cookies = ""
                channel.extra_credentials = {}
                channel.credentials_updated_at = datetime.now()
                channel.credentials_updated_by = ""
                session.commit()
            self.invalidate_cache()
            self._cache.clear()
            self._cache_ttl.clear()
            return True
        except Exception as e:
            logger.error(f"清除渠道凭证失败: {e}")
            return False

    def verify_credential(self, channel_code: str) -> dict:
        """
        验证凭证有效性。

        返回格式：{"success": bool, "message": str, "response_code": int}
        """
        cookie, _ = self.get_cookie(channel_code)
        if not cookie:
            return {"success": False, "message": "凭证未配置", "response_code": 0}

        test_urls = {
            "weibo": "https://weibo.com/ajax/statuses/hot_band",
            "zhihu": "https://www.zhihu.com/api/v4/members/self?include=url_token",
            "xiaohongshu": "https://edith.xiaohongshu.com/api/sns/web/v2/user/me",
        }

        test_url = test_urls.get(channel_code)
        if not test_url:
            return {"success": False, "message": "不支持验证的渠道", "response_code": 0}

        headers = {"Cookie": cookie, "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

        if channel_code == "weibo":
            headers["Referer"] = "https://weibo.com/"
            headers["Accept"] = "application/json"

        # 知乎测试连接不需要 zse 签名头（zse 对 /members/self 反而触发 403），
        # 仅用 Cookie 即可判断登录态是否有效。
        if channel_code == "zhihu":
            headers["Referer"] = "https://www.zhihu.com/"
            headers["Accept"] = "application/json, text/plain, */*"

        try:
            response = httpx.get(test_url, headers=headers, timeout=10, follow_redirects=True)
            response_text = response.text

            # 根据响应判断凭证有效性
            if channel_code == "weibo":
                if response.status_code == 200 and '"ok":1' in response_text:
                    self._update_cookie_status(channel_code, "active")
                    return {"success": True, "message": "凭证有效", "response_code": response.status_code}
                elif response.status_code in (401, 403) or "登录" in response_text or "请登录" in response_text:
                    self._update_cookie_status(channel_code, "expired")
                    return {"success": False, "message": "凭证已过期", "response_code": response.status_code}
                else:
                    self._update_cookie_status(channel_code, "invalid")
                    return {"success": False, "message": f"凭证无效，响应状态: {response.status_code}，响应: {response_text[:100]}", "response_code": response.status_code}

            elif channel_code == "zhihu":
                if response.status_code == 200 and ('"id":' in response_text or '"url_token":' in response_text):
                    self._update_cookie_status(channel_code, "active")
                    return {"success": True, "message": "凭证有效", "response_code": response.status_code}
                elif response.status_code == 401 or "登录" in response_text or "需要登录" in response_text:
                    self._update_cookie_status(channel_code, "expired")
                    return {"success": False, "message": "凭证已过期", "response_code": response.status_code}
                else:
                    self._update_cookie_status(channel_code, "invalid")
                    return {"success": False, "message": f"凭证无效，响应状态: {response.status_code}，响应: {response_text[:100]}", "response_code": response.status_code}

            elif channel_code == "xiaohongshu":
                if '"code":0' in response_text or '"userId":' in response_text:
                    self._update_cookie_status(channel_code, "active")
                    return {"success": True, "message": "凭证有效", "response_code": response.status_code}
                elif "登录" in response_text or "需要登录" in response_text:
                    self._update_cookie_status(channel_code, "expired")
                    return {"success": False, "message": "凭证已过期", "response_code": response.status_code}
                else:
                    self._update_cookie_status(channel_code, "invalid")
                    return {"success": False, "message": f"凭证无效，响应状态: {response.status_code}", "response_code": response.status_code}

            return {"success": False, "message": f"未知响应，状态码: {response.status_code}", "response_code": response.status_code}

        except httpx.TimeoutException:
            return {"success": False, "message": "验证超时", "response_code": 0}
        except httpx.RequestError as e:
            return {"success": False, "message": f"请求失败: {str(e)}", "response_code": 0}
        except Exception as e:
            return {"success": False, "message": f"验证异常: {str(e)}", "response_code": 0}

    def _update_cookie_status(self, channel_code: str, status: str) -> None:
        """更新 Cookie 状态标记。"""
        if not self._session_factory:
            return

        try:
            from database import get_session, Channel
            import json as json_mod

            with get_session() as session:
                channel = session.query(Channel).filter(Channel.code == channel_code).first()
                if channel and channel.cookies:
                    try:
                        cookie_data = json_mod.loads(channel.cookies) if isinstance(channel.cookies, str) else channel.cookies
                    except json_mod.JSONDecodeError:
                        cookie_data = {"cookie": channel.cookies}

                    cookie_data["status"] = status
                    cookie_data["last_verified_at"] = datetime.now().isoformat()
                    channel.cookies = json_mod.dumps(cookie_data, ensure_ascii=False)
                    session.commit()
        except Exception as e:
            logger.warning(f"更新 Cookie 状态失败: {e}")

    def _read_db_credential(self, name: str) -> _DatabaseCredentialRead:
        """从数据库读取凭证。"""
        mapping = ENV_VAR_TO_CHANNEL_CREDENTIAL.get(name)
        if not mapping:
            return _DatabaseCredentialRead(found=False)

        channel_code, credential_key = mapping

        if not self._session_factory:
            return _DatabaseCredentialRead(found=False)

        try:
            from database import get_session, Channel

            with get_session() as session:
                channel = session.query(Channel).filter(Channel.code == channel_code).first()
                if not channel:
                    return _DatabaseCredentialRead(found=False)

                if credential_key == "cookie":
                    cookies_data = None
                    if channel.cookies:
                        try:
                            cookies_data = json.loads(channel.cookies) if isinstance(channel.cookies, str) else channel.cookies
                        except json.JSONDecodeError:
                            cookies_data = {"cookie": channel.cookies}
                    credential_status = cookies_data.get("status", "") if isinstance(cookies_data, dict) else ""
                    if _is_sample_cookie_data(cookies_data):
                        return _DatabaseCredentialRead(
                            found=True,
                            channel_code=channel_code,
                            credential_key=credential_key,
                            status=credential_status,
                        )
                    return _DatabaseCredentialRead(
                        found=bool(cookies_data),
                        value=cookies_data.get("cookie", "") if cookies_data else "",
                        channel_code=channel_code,
                        credential_key=credential_key,
                        status=credential_status,
                    )
                elif credential_key.startswith("zse_"):
                    if _is_sample_cookie_data(_parse_cookie_data(channel.cookies)):
                        return _DatabaseCredentialRead(
                            found=True,
                            channel_code=channel_code,
                            credential_key=credential_key,
                            status="sample",
                        )
                    extra = channel.extra_credentials or {}
                    # 支持两种存储格式：
                    # 扁平格式: {"ZHIHU_ZSE_93": "...", "ZHIHU_ZSE_96": "..."}
                    # 嵌套格式: {"zhihu": {"zse_93": "...", "zse_96": "..."}}
                    env_name = f"ZHIHU_{credential_key.upper()}"
                    flat_value = extra.get(env_name, "")
                    zhihu_nested = extra.get("zhihu", {})
                    nested_value = zhihu_nested.get(credential_key, "")
                    value = flat_value or nested_value
                    status = zhihu_nested.get("status", "") if isinstance(zhihu_nested, dict) else ""
                    if _is_sample_credential_status(status):
                        return _DatabaseCredentialRead(
                            found=True,
                            channel_code=channel_code,
                            credential_key=credential_key,
                            status=status,
                        )
                    return _DatabaseCredentialRead(
                        found=bool(value),
                        value=value,
                        channel_code=channel_code,
                        credential_key=credential_key,
                        status=status,
                    )
                else:
                    return _DatabaseCredentialRead(found=False)

        except Exception as e:
            logger.warning(f"从数据库读取凭证失败 {name}: {e}")
            return _DatabaseCredentialRead(found=False)

    def _get_cached(self, name: str) -> Optional[tuple[str, str]]:
        """获取缓存的凭证（未过期）。"""
        if name not in self._cache:
            return None

        cached_time = self._cache_ttl.get(name)
        if cached_time and (datetime.now() - cached_time).total_seconds() < self._cache_duration_seconds:
            return self._cache[name]
        return None

    def _set_cache(self, name: str, value: tuple[str, str]) -> None:
        """设置凭证缓存。"""
        self._cache[name] = value
        self._cache_ttl[name] = datetime.now()

    def _log_credential_state(self, name: str, credential: _DatabaseCredentialRead, enabled: bool) -> None:
        """打印脱敏凭证读取状态，避免日志泄露 Cookie 明文。"""
        state = (
            name,
            credential.source,
            credential.status or "",
            len(credential.value or ""),
            enabled,
        )
        if state in self._logged_states:
            return
        self._logged_states.add(state)
        if enabled:
            logger.info(
                "渠道凭证已读取: channel=%s key=%s source=%s status=%s length=%s",
                credential.channel_code,
                credential.credential_key,
                credential.source,
                credential.status or "unknown",
                len(credential.value or ""),
            )
        else:
            logger.warning(
                "渠道凭证未启用: channel=%s key=%s source=%s status=%s length=%s",
                credential.channel_code,
                credential.credential_key,
                credential.source,
                credential.status or "empty",
                len(credential.value or ""),
            )

    def _log_mapped_credential_state(self, name: str, value: str, source: str, status: str) -> None:
        mapping = ENV_VAR_TO_CHANNEL_CREDENTIAL.get(name)
        if not mapping:
            return
        channel_code, credential_key = mapping
        self._log_credential_state(
            name,
            _DatabaseCredentialRead(
                found=True,
                value=value,
                channel_code=channel_code,
                credential_key=credential_key,
                status=status,
                source=source,
            ),
            bool(value),
        )

    def _get_cookies_metadata(self, env_name: str) -> dict:
        """从数据库获取 cookies 的元数据（状态、验证时间）。"""
        mapping = ENV_VAR_TO_CHANNEL_CREDENTIAL.get(env_name)
        if not mapping:
            return {}

        channel_code, credential_key = mapping
        if credential_key != "cookie" or not self._session_factory:
            return {}

        try:
            from database import get_session, Channel

            with get_session() as session:
                channel = session.query(Channel).filter(Channel.code == channel_code).first()
                if channel and channel.cookies:
                    try:
                        cookies_data = json.loads(channel.cookies) if isinstance(channel.cookies, str) else channel.cookies
                        return {
                            "status": cookies_data.get("status", "unknown"),
                            "last_verified_at": cookies_data.get("last_verified_at"),
                        }
                    except json.JSONDecodeError:
                        return {}
        except Exception:
            pass
        return {}

    def _read_env_file_value(self, env_file: Path, name: str) -> str:
        if not env_file.exists():
            return ""
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, raw_value = stripped.split("=", 1)
                if key.strip() == name:
                    return _strip_env_quotes(raw_value)
        except OSError:
            return ""
        return ""


def get_credential(name: str) -> str:
    """便捷函数：获取单个凭证值。"""
    provider = CredentialProvider.get_instance(session_factory=_default_session_factory())
    return provider.get(name)


def build_credential_report(channel_codes: list[str] | None = None) -> dict:
    """便捷函数：生成所有渠道的凭证健康报告。"""
    provider = CredentialProvider.get_instance(session_factory=_default_session_factory())
    return provider.all_channel_reports(channel_codes)


def _default_session_factory():
    try:
        from database import get_session

        return get_session
    except Exception:
        return None


def _credential_health(configured: bool, required: bool) -> str:
    if configured:
        return "configured"
    if required:
        return "missing_required"
    return "not_configured"


def _parse_cookie_data(value) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {"cookie": value}


def _is_sample_credential_status(status: str) -> bool:
    return (status or "").strip().lower() in {"sample", "placeholder", "example"}


def _is_sample_cookie_data(cookies_data: dict | None) -> bool:
    if not cookies_data:
        return False
    return _is_sample_credential_status(str(cookies_data.get("status", "")))


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return "***"
    return f"{value[:4]}...{value[-4:]}"

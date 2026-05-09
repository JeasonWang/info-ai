from dataclasses import dataclass
import os
from pathlib import Path


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


CHANNEL_CREDENTIAL_SPECS: dict[str, tuple[CredentialSpec, ...]] = {
    "weibo": (CredentialSpec("WEIBO_COOKIE", required=True),),
    "zhihu": (
        CredentialSpec("ZHIHU_COOKIE", required=True),
        CredentialSpec("ZHIHU_ZSE_93", required=False),
        CredentialSpec("ZHIHU_ZSE_96", required=False),
    ),
    "xiaohongshu": (CredentialSpec("XHS_COOKIE", required=True),),
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
    """统一读取采集凭证，避免每个爬虫重复解析 .env。"""

    def __init__(self, env_files: list[Path] | None = None):
        self.env_files = env_files or _candidate_env_files()

    def get(self, name: str) -> str:
        return self.get_with_source(name)[0]

    def get_with_source(self, name: str) -> tuple[str, str]:
        env_value = os.getenv(name, "").strip()
        if env_value:
            return _strip_env_quotes(env_value), "environment"

        for env_file in self.env_files:
            value = self._read_env_file_value(env_file, name)
            if value:
                return value, str(env_file)
        return "", ""

    def status(self, spec: CredentialSpec) -> CredentialStatus:
        value, source = self.get_with_source(spec.name)
        configured = bool(value)
        return CredentialStatus(
            name=spec.name,
            configured=configured,
            source=source,
            required=spec.required,
            length=len(value),
            preview=_mask_secret(value),
            health=_credential_health(configured=configured, required=spec.required),
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
    return CredentialProvider().get(name)


def build_credential_report(channel_codes: list[str] | None = None) -> dict:
    return CredentialProvider().all_channel_reports(channel_codes)


def _credential_health(configured: bool, required: bool) -> str:
    if configured:
        return "configured"
    if required:
        return "missing_required"
    return "not_configured"


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return "***"
    return f"{value[:4]}...{value[-4:]}"

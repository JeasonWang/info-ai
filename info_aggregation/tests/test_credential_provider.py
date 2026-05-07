from pathlib import Path

from services.credential_provider import CredentialProvider, CredentialSpec, build_credential_report


def test_credential_provider_prefers_environment_value(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("WEIBO_COOKIE=file-cookie\n", encoding="utf-8")
    monkeypatch.setenv("WEIBO_COOKIE", "env-cookie")

    provider = CredentialProvider(env_files=[env_file])

    assert provider.get_with_source("WEIBO_COOKIE") == ("env-cookie", "environment")


def test_credential_provider_reads_quoted_env_file_value(monkeypatch, tmp_path):
    monkeypatch.delenv("XHS_COOKIE", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("XHS_COOKIE='xhs-cookie-value'\n", encoding="utf-8")

    provider = CredentialProvider(env_files=[env_file])

    assert provider.get("XHS_COOKIE") == "xhs-cookie-value"


def test_credential_status_masks_secret(monkeypatch, tmp_path):
    monkeypatch.delenv("ZHIHU_COOKIE", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("ZHIHU_COOKIE=abcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")

    status = CredentialProvider(env_files=[env_file]).status(CredentialSpec("ZHIHU_COOKIE", required=True))

    assert status.configured is True
    assert status.preview == "abcd...wxyz"
    assert status.health == "configured"


def test_channel_credential_report_marks_missing_required(monkeypatch):
    monkeypatch.delenv("WEIBO_COOKIE", raising=False)

    report = CredentialProvider(env_files=[Path("/tmp/not-exists")]).channel_report("weibo")

    assert report["health"] == "missing_required"
    assert report["missing_required"] == ["WEIBO_COOKIE"]


def test_build_credential_report_includes_not_required_channel():
    report = build_credential_report(["toutiao"])

    assert report["toutiao"]["health"] == "not_required"
    assert report["toutiao"]["credentials"] == []

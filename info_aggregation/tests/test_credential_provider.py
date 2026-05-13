from pathlib import Path

from services.collection.credential_provider import CredentialProvider, CredentialSpec, build_credential_report
from database import Category, Channel, get_session


def test_credential_provider_uses_environment_as_legacy_fallback(monkeypatch, tmp_path):
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


def test_credential_provider_reads_and_clears_database_credentials(monkeypatch, session):
    monkeypatch.delenv("WEIBO_COOKIE", raising=False)
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    channel = Channel(
        name="微博",
        code="weibo",
        base_url="https://weibo.com",
        category_id=category.id,
        cookies='{"cookie": "db-cookie", "status": "active"}',
        is_active=1,
    )
    session.add(channel)
    session.commit()

    provider = CredentialProvider(env_files=[Path("/tmp/not-exists")], session_factory=get_session)

    assert provider.get_with_source("WEIBO_COOKIE") == ("db-cookie", "database")
    assert provider.get_channel_credential_info("weibo").cookie_configured is True

    assert provider.delete_channel_credentials("weibo") is True
    CredentialProvider.invalidate_cache()

    assert provider.get_with_source("WEIBO_COOKIE") == ("", "")
    assert provider.get_channel_credential_info("weibo").cookie_configured is False


def test_credential_provider_prefers_database_over_legacy_env(monkeypatch, session):
    monkeypatch.setenv("WEIBO_COOKIE", "env-cookie")
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    session.add(
        Channel(
            name="微博",
            code="weibo",
            base_url="https://weibo.com",
            category_id=category.id,
            cookies='{"cookie": "db-cookie", "status": "active"}',
            is_active=1,
        )
    )
    session.commit()

    provider = CredentialProvider(env_files=[Path("/tmp/not-exists")], session_factory=get_session)

    assert provider.get_with_source("WEIBO_COOKIE") == ("db-cookie", "database")


def test_sample_database_credentials_are_visible_but_not_runtime_credentials(monkeypatch, session):
    monkeypatch.delenv("ZHIHU_COOKIE", raising=False)
    monkeypatch.delenv("ZHIHU_ZSE_93", raising=False)
    monkeypatch.delenv("ZHIHU_ZSE_96", raising=False)
    category = Category(name="AI大模型", code="ai", description="AI")
    session.add(category)
    session.flush()
    session.add(
        Channel(
            name="知乎",
            code="zhihu",
            base_url="https://www.zhihu.com",
            category_id=category.id,
            cookies='{"cookie": "z_c0=sample; d_c0=sample", "status": "sample"}',
            extra_credentials={"zhihu": {"zse_93": "101_3_3.0", "zse_96": "2.0_sample", "status": "sample"}},
            is_active=1,
        )
    )
    session.commit()

    provider = CredentialProvider(env_files=[Path("/tmp/not-exists")], session_factory=get_session)
    info = provider.get_channel_credential_info("zhihu")

    assert provider.get_with_source("ZHIHU_COOKIE") == ("", "")
    assert provider.get_with_source("ZHIHU_ZSE_96") == ("", "")
    assert info.cookie_status == "sample"
    assert info.cookie_preview
    assert info.cookie_configured is False


def test_sample_database_credentials_block_legacy_env_fallback(monkeypatch, session):
    monkeypatch.setenv("WEIBO_COOKIE", "env-cookie")
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    session.add(
        Channel(
            name="微博",
            code="weibo",
            base_url="https://weibo.com",
            category_id=category.id,
            cookies='{"cookie": "SUB=sample", "status": "sample"}',
            is_active=1,
        )
    )
    session.commit()

    provider = CredentialProvider(env_files=[Path("/tmp/not-exists")], session_factory=get_session)

    assert provider.get_with_source("WEIBO_COOKIE") == ("", "")


def test_updating_sample_cookie_promotes_status_to_active(monkeypatch, session):
    monkeypatch.delenv("WEIBO_COOKIE", raising=False)
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()
    session.add(
        Channel(
            name="微博",
            code="weibo",
            base_url="https://weibo.com",
            category_id=category.id,
            cookies='{"cookie": "SUB=sample", "status": "sample"}',
            is_active=1,
        )
    )
    session.commit()

    provider = CredentialProvider(env_files=[Path("/tmp/not-exists")], session_factory=get_session)

    assert provider.update_channel_credentials("weibo", cookies="SUB=real-cookie", updated_by="admin") is True
    assert provider.get_with_source("WEIBO_COOKIE") == ("SUB=real-cookie", "database")
    assert provider.get_channel_credential_info("weibo").cookie_status == "active"


def test_updating_sample_zhihu_extra_promotes_status_to_active(session):
    category = Category(name="AI大模型", code="ai", description="AI")
    session.add(category)
    session.flush()
    session.add(
        Channel(
            name="知乎",
            code="zhihu",
            base_url="https://www.zhihu.com",
            category_id=category.id,
            cookies='{"cookie": "z_c0=sample", "status": "sample"}',
            extra_credentials={"zhihu": {"zse_93": "101_3_3.0", "zse_96": "2.0_sample", "status": "sample"}},
            is_active=1,
        )
    )
    session.commit()

    provider = CredentialProvider(env_files=[Path("/tmp/not-exists")], session_factory=get_session)

    assert provider.update_channel_credentials(
        "zhihu",
        cookies="z_c0=real-cookie",
        extra_credentials={"zhihu": {"zse_93": "101_3_3.0", "zse_96": "2.0_real", "status": "sample"}},
        updated_by="admin",
    ) is True
    assert provider.get_with_source("ZHIHU_COOKIE") == ("z_c0=real-cookie", "database")
    assert provider.get_with_source("ZHIHU_ZSE_96") == ("2.0_real", "database")

from datetime import date

from database import LLMModelConfig
from services.analysis.llm_model_config import (
    create_llm_model_config,
    list_llm_model_configs,
    select_available_llm_config,
    update_llm_model_config,
)


def test_llm_model_config_crud_masks_api_key_and_preserves_empty_update(session):
    config = create_llm_model_config(
        session,
        {
            "provider_name": "千问",
            "provider_code": "qwen",
            "base_url": "http://127.0.0.1:8001/v1",
            "api_key": "sk-qwen-secret",
            "model_name": "qwen2.5-14b-instruct",
            "is_enabled": 1,
            "daily_call_limit": 100,
        },
    )

    listed = list_llm_model_configs(session)

    assert listed[0]["id"] == config.id
    assert listed[0]["api_key"] == "sk-q...cret"
    assert listed[0]["daily_call_count"] == 0

    update_llm_model_config(session, config.id, {"api_key": "", "model_name": "qwen3-local"})
    session.refresh(config)
    assert config.api_key == "sk-qwen-secret"
    assert config.model_name == "qwen3-local"


def test_select_available_llm_config_skips_disabled_and_daily_limited(session):
    session.add_all(
        [
            LLMModelConfig(
                provider_name="DeepSeek",
                provider_code="deepseek",
                base_url="https://api.deepseek.com/v1",
                api_key="sk-deepseek",
                model_name="deepseek-chat",
                is_enabled=1,
                daily_call_limit=1,
                daily_call_count=1,
                last_call_date=date.today(),
            ),
            LLMModelConfig(
                provider_name="千问",
                provider_code="qwen",
                base_url="http://127.0.0.1:8001/v1",
                api_key="sk-qwen",
                model_name="qwen2.5-14b-instruct",
                is_enabled=1,
                daily_call_limit=10,
                daily_call_count=3,
                last_call_date=date.today(),
            ),
            LLMModelConfig(
                provider_name="关闭模型",
                provider_code="off",
                base_url="http://127.0.0.1:9000/v1",
                api_key="",
                model_name="off-model",
                is_enabled=0,
                daily_call_limit=10,
            ),
        ]
    )
    session.commit()

    selected = select_available_llm_config(session)

    assert selected.provider_code == "qwen"


def test_select_available_llm_config_resets_yesterday_count(session):
    session.add(
        LLMModelConfig(
            provider_name="千问",
            provider_code="qwen",
            base_url="http://127.0.0.1:8001/v1",
            api_key="",
            model_name="qwen-local",
            is_enabled=1,
            daily_call_limit=2,
            daily_call_count=2,
            last_call_date=date(2026, 1, 1),
        )
    )
    session.commit()

    selected = select_available_llm_config(session)

    assert selected is not None
    assert selected.daily_call_count == 0
    assert selected.last_call_date == date.today()

from datetime import date

from fastapi.testclient import TestClient

from api import app
from database import LLMCallLog, LLMModelConfig
from services.llm.chat import LLMChatResult, run_llm_chat_completion, run_llm_chat_test


def _seed_enabled_config(session):
    config = LLMModelConfig(
        provider_name="千问",
        provider_code="qwen",
        base_url="http://127.0.0.1:8001/v1",
        api_key="sk-qwen",
        model_name="qwen-local",
        is_enabled=1,
        daily_call_limit=10,
        daily_call_count=0,
        last_call_date=date.today(),
        priority=10,
    )
    session.add(config)
    session.commit()
    return config


def test_run_llm_chat_test_records_success_without_reusing_request_session(session, monkeypatch):
    config = _seed_enabled_config(session)

    def fake_chat(self, request):
        return LLMChatResult(
            config_id=self.config.id,
            provider_code=self.config.provider_code,
            model_name=self.config.model_name,
            content='{"ok":true,"summary":"pong"}',
            latency_ms=1234,
            status_code=200,
            usage={"total_tokens": 12},
            raw_response={},
        )

    monkeypatch.setattr("services.llm.chat.OpenAICompatibleChatClient.chat", fake_chat)

    result = run_llm_chat_test("ping", config_id=config.id, timeout_seconds=180)

    assert result["ok"] is True
    assert result["config_id"] == config.id
    assert result["json"] == {"ok": True, "summary": "pong"}
    session.refresh(config)
    assert config.daily_call_count == 1
    log = session.query(LLMCallLog).one()
    assert log.status == "succeeded"
    assert log.latency_ms == 1234
    assert log.request_payload["messages"][-1]["content"] == "ping"
    assert log.response_content == '{"ok":true,"summary":"pong"}'


def test_run_llm_chat_test_returns_failure_payload_and_call_log(session, monkeypatch):
    config = _seed_enabled_config(session)

    def fail_chat(self, request):
        raise TimeoutError("model timeout")

    monkeypatch.setattr("services.llm.chat.OpenAICompatibleChatClient.chat", fail_chat)

    result = run_llm_chat_test("ping", config_id=config.id, timeout_seconds=180)

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert "model timeout" in result["message"]
    log = session.query(LLMCallLog).one()
    assert log.status == "failed"
    assert log.error_message == "model timeout"
    assert log.request_payload["messages"][-1]["content"] == "ping"


def test_run_llm_chat_completion_records_plain_chat_request_and_answer(session, monkeypatch):
    config = _seed_enabled_config(session)

    def fake_chat(self, request):
        assert request.response_format is None
        assert request.messages[-1].content == "介绍一下这个系统"
        return LLMChatResult(
            config_id=self.config.id,
            provider_code=self.config.provider_code,
            model_name=self.config.model_name,
            content="这是一个信息聚合和事件分析系统。",
            latency_ms=4321,
            status_code=200,
            usage={"total_tokens": 18},
            raw_response={"choices": [{"message": {"content": "这是一个信息聚合和事件分析系统。"}}]},
        )

    monkeypatch.setattr("services.llm.chat.OpenAICompatibleChatClient.chat", fake_chat)

    result = run_llm_chat_completion("介绍一下这个系统", config_id=config.id, timeout_seconds=180)

    assert result["ok"] is True
    assert result["answer"] == "这是一个信息聚合和事件分析系统。"
    log = session.query(LLMCallLog).one()
    assert log.status == "succeeded"
    assert log.request_payload["context"] == {"source": "admin_chat"}
    assert log.request_payload["messages"][-1]["content"] == "介绍一下这个系统"
    assert log.response_content == "这是一个信息聚合和事件分析系统。"
    assert log.response_payload["choices"][0]["message"]["content"] == "这是一个信息聚合和事件分析系统。"


def test_internal_llm_chat_test_api_returns_nonzero_code_for_model_failure(session, monkeypatch):
    config = _seed_enabled_config(session)

    def fail_chat(self, request):
        raise TimeoutError("model timeout")

    monkeypatch.setattr("services.llm.chat.OpenAICompatibleChatClient.chat", fail_chat)
    client = TestClient(app)

    response = client.post(
        "/api/internal/llm/chat-test",
        json={"config_id": config.id, "prompt": "ping", "timeout_seconds": 180},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 1
    assert payload["data"]["ok"] is False
    assert "model timeout" in payload["message"]


def test_internal_llm_chat_api_returns_plain_answer(session, monkeypatch):
    config = _seed_enabled_config(session)

    def fake_chat(self, request):
        return LLMChatResult(
            config_id=self.config.id,
            provider_code=self.config.provider_code,
            model_name=self.config.model_name,
            content="你好，我是信息达人助手。",
            latency_ms=800,
            status_code=200,
            usage={},
            raw_response={},
        )

    monkeypatch.setattr("services.llm.chat.OpenAICompatibleChatClient.chat", fake_chat)
    client = TestClient(app)

    response = client.post(
        "/api/internal/llm/chat",
        json={"config_id": config.id, "message": "你好", "timeout_seconds": 180},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["answer"] == "你好，我是信息达人助手。"

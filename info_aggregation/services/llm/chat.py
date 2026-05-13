import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from config import EVENT_ANALYSIS_TEMPERATURE, EVENT_ANALYSIS_TIMEOUT
from services.analysis.llm_model_config import (
    LLMModelConfigSnapshot,
    get_llm_config_snapshot_independent,
    record_llm_call_failure_independent,
    record_llm_call_success_independent,
    select_available_llm_config_independent,
)


@dataclass(frozen=True)
class LLMChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMChatRequest:
    messages: list[LLMChatMessage]
    temperature: float = EVENT_ANALYSIS_TEMPERATURE
    response_format: dict[str, Any] | None = None
    timeout_seconds: int = EVENT_ANALYSIS_TIMEOUT
    input_item_count: int = 1
    log_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMChatResult:
    config_id: int
    provider_code: str
    model_name: str
    content: str
    latency_ms: int
    status_code: int
    usage: dict[str, Any]
    raw_response: dict[str, Any]


def _message_to_dict(message: LLMChatMessage) -> dict[str, str]:
    return {"role": message.role, "content": message.content}


def _request_log_payload(config: LLMModelConfigSnapshot, request: LLMChatRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model_name,
        "temperature": request.temperature,
        "messages": [_message_to_dict(message) for message in request.messages],
    }
    if request.response_format:
        payload["response_format"] = request.response_format
    if request.log_context:
        payload["context"] = request.log_context
    return payload


class OpenAICompatibleChatClient:
    def __init__(self, config: LLMModelConfigSnapshot):
        self.config = config

    def chat(self, request: LLMChatRequest) -> LLMChatResult:
        started = time.perf_counter()
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload: dict[str, Any] = {
            "model": self.config.model_name,
            "temperature": request.temperature,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
        }
        if request.response_format:
            payload["response_format"] = request.response_format
        response = httpx.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=httpx.Timeout(float(request.timeout_seconds), connect=15.0),
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}
        response.raise_for_status()
        content = data["choices"][0]["message"]["content"]
        return LLMChatResult(
            config_id=self.config.id,
            provider_code=self.config.provider_code or "openai_compatible",
            model_name=self.config.model_name,
            content=content,
            latency_ms=latency_ms,
            status_code=response.status_code,
            usage=data.get("usage") if isinstance(data.get("usage"), dict) else {},
            raw_response=data,
        )


def run_llm_chat(
    config: LLMModelConfigSnapshot,
    request: LLMChatRequest,
    record_call: bool = True,
) -> LLMChatResult:
    started = time.perf_counter()
    request_payload = _request_log_payload(config, request)
    try:
        result = OpenAICompatibleChatClient(config).chat(request)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        if record_call:
            try:
                response_payload = None
                response_content = ""
                response = getattr(exc, "response", None)
                if response is not None:
                    try:
                        parsed = response.json()
                        if isinstance(parsed, dict):
                            response_payload = parsed
                        else:
                            response_payload = {"response": parsed}
                    except Exception:
                        response_content = getattr(response, "text", "") or ""
                record_llm_call_failure_independent(
                    config.id,
                    latency_ms,
                    request.input_item_count,
                    str(exc),
                    request_payload=request_payload,
                    response_content=response_content,
                    response_payload=response_payload,
                )
            except Exception:
                pass
        raise
    if record_call:
        try:
            record_llm_call_success_independent(
                config.id,
                result.latency_ms,
                request.input_item_count,
                request_payload=request_payload,
                response_content=result.content,
                response_payload=result.raw_response,
            )
        except Exception:
            pass
    return result


def run_llm_chat_completion(
    prompt: str,
    config_id: int | None = None,
    timeout_seconds: int | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    config = (
        get_llm_config_snapshot_independent(config_id, require_enabled=True)
        if config_id
        else select_available_llm_config_independent()
    )
    if config is None:
        return {
            "ok": False,
            "status": "no_available_model",
            "message": "没有可用的大模型配置",
        }
    request = LLMChatRequest(
        messages=[
            LLMChatMessage(role="system", content=system_prompt or "你是信息达人后台的通用对话助手，请直接、清晰地回答用户问题。"),
            LLMChatMessage(role="user", content=prompt),
        ],
        timeout_seconds=timeout_seconds or EVENT_ANALYSIS_TIMEOUT,
        log_context={"source": "admin_chat"},
    )
    started = time.perf_counter()
    try:
        result = run_llm_chat(config, request)
    except Exception as exc:
        return {
            "ok": False,
            "status": "failed",
            "config_id": config.id,
            "provider_code": config.provider_code,
            "model_name": config.model_name,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "message": str(exc),
        }
    parsed: Any | None = None
    try:
        parsed = json.loads(result.content)
    except json.JSONDecodeError:
        parsed = None
    return {
        "ok": True,
        "status": "succeeded",
        "answer": result.content,
        "config_id": result.config_id,
        "provider_code": result.provider_code,
        "model_name": result.model_name,
        "latency_ms": result.latency_ms,
        "status_code": result.status_code,
        "content": result.content,
        "json": parsed,
        "usage": result.usage,
    }


def run_llm_chat_test(
    prompt: str,
    config_id: int | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    return run_llm_chat_completion(
        prompt=prompt,
        config_id=config_id,
        timeout_seconds=timeout_seconds,
        system_prompt="你是信息达人后台的大模型连通性测试助手，请用简洁中文回答。",
    )

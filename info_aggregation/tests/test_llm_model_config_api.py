from fastapi.testclient import TestClient

from api import app


def test_admin_llm_model_config_api_masks_secret_and_preserves_empty_update(session):
    client = TestClient(app)

    response = client.post(
        "/api/admin/llm-model-configs",
        json={
            "provider_name": "千问",
            "provider_code": "qwen",
            "base_url": "http://127.0.0.1:8001/v1",
            "api_key": "sk-qwen-secret",
            "model_name": "qwen-local",
            "is_enabled": 1,
            "daily_call_limit": 100,
            "daily_call_count": 0,
            "priority": 10,
        },
    )

    assert response.status_code == 200
    item = response.json()["data"]
    assert item["api_key"] == "sk-q...cret"

    update_response = client.put(
        f"/api/admin/llm-model-configs/{item['id']}",
        json={
            "provider_name": "千问",
            "provider_code": "qwen",
            "base_url": "http://127.0.0.1:8001/v1",
            "api_key": "",
            "model_name": "qwen-new",
            "is_enabled": 0,
            "daily_call_limit": 50,
            "daily_call_count": 0,
            "priority": 20,
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["model_name"] == "qwen-new"
    assert updated["api_key"] == "sk-q...cret"

    list_response = client.get("/api/admin/llm-model-configs")
    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["provider_code"] == "qwen"

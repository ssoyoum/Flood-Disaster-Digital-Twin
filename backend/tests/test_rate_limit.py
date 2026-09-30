from fastapi.testclient import TestClient

from app import agent_runner
from app.main import app

client = TestClient(app)


def test_agent_ask_is_rate_limited_per_client(monkeypatch):
    monkeypatch.setenv("FLOODOPS_AGENT_PER_MINUTE", "2")
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: agent_runner.AgentAction(
        action="final", gap_kind="outside_scope", answer="계산할 수 없는 질문입니다."))
    headers = {"X-Forwarded-For": "203.0.113.7"}
    body = {"event_id": "osong-2023", "message": "아무 질문"}
    assert client.post("/api/agent/ask", json=body, headers=headers).status_code == 200
    assert client.post("/api/agent/ask", json=body, headers=headers).status_code == 200
    blocked = client.post("/api/agent/ask", json=body, headers=headers)
    assert blocked.status_code == 429
    assert "1분 뒤" in blocked.json()["detail"]
    other = client.post("/api/agent/ask", json=body, headers={"X-Forwarded-For": "198.51.100.9"})
    assert other.status_code == 200

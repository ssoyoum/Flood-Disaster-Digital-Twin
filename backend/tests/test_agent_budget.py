"""Exercise wall-clock cancellation, shared retries and safe API diagnostics."""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import agent_runner
from app.main import app
from app.schemas import AgentAskRequest
from app.services import ReconstructionUnavailable


def _decision(**decision):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(decision)}]}}]})


def _enable_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-not-for-diagnostics")
    monkeypatch.setattr(agent_runner, "llm_planner_status", lambda: {"available": True})
    monkeypatch.setenv("AGENT_ASK_TIMEOUT_SECONDS", "25")


def test_wall_clock_timeout_cancels_the_inflight_http_request(monkeypatch):
    cancelled = []

    class SlowClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            try:
                await asyncio.sleep(60)
            finally:
                cancelled.append(True)

    monkeypatch.setattr(agent_runner.httpx, "AsyncClient", SlowClient)
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(agent_runner._post_gemini("https://example.invalid", headers={}, json={}, timeout=0.02))
    assert cancelled == [True]


def test_json_retry_cannot_start_a_fresh_budget_and_tools_remain_available(monkeypatch):
    _enable_model(monkeypatch)
    now = [100.0]
    monkeypatch.setattr(agent_runner.time, "monotonic", lambda: now[0])
    requests = []

    async def malformed(*args, **kwargs):
        requests.append(kwargs["timeout"])
        now[0] += 26
        return httpx.Response(200, json={"candidates": []})

    monkeypatch.setattr(agent_runner, "_post_gemini", malformed)
    result = agent_runner.ask_agent(AgentAskRequest(message="08:20에 통제했다면?"))
    assert requests == [25.0]
    assert result["status"] == "ANSWERED"
    assert result["tool_calls"][0]["tool_name"] == "analyze_closure_timing"
    assert result["tool_calls"][0]["result"]["scenarios"][0]["minutes_before_underpass_inflow"] == 7
    assert result["diagnostics"]["completion_source"] == "registered_tools"
    assert result["diagnostics"]["model_requests"] == 1
    assert [failure["code"] for failure in result["diagnostics"]["failures"]] == [
        "model_invalid_decision", "model_budget_exceeded",
    ]
    assert "test-secret" not in json.dumps(result["diagnostics"])


def test_all_model_steps_share_one_deadline(monkeypatch):
    _enable_model(monkeypatch)
    now = [100.0]
    monkeypatch.setattr(agent_runner.time, "monotonic", lambda: now[0])
    timeouts = []
    actions = iter([
        _decision(action="tool", tool_name="get_event"),
        _decision(action="tool", tool_name="get_reconstruction"),
        _decision(action="final", answer="질문한 사건의 연결 자료를 확인했습니다 [1].", evidence_calls=[1]),
    ])
    elapsed = iter([10, 10, 1])

    async def post(*args, **kwargs):
        timeouts.append(kwargs["timeout"])
        now[0] += next(elapsed)
        return next(actions)

    monkeypatch.setattr(agent_runner, "_post_gemini", post)
    result = agent_runner.ask_agent(AgentAskRequest(message="연결 자료를 확인해줘"))
    assert timeouts == [25.0, 15.0, 5.0]
    assert result["diagnostics"]["model_steps"] == 3
    assert result["diagnostics"]["model_requests"] == 3
    assert result["diagnostics"]["completion_source"] == "model"


def test_api_distinguishes_input_rejection_from_tool_failure_and_resets_state(monkeypatch):
    actions = iter([
        agent_runner.AgentAction(action="tool", tool_name="made-up-tool"),
        agent_runner.AgentAction(action="tool", tool_name="get_event"),
        agent_runner.AgentAction(action="final", gap_kind="unconnected_data", answer="연결된 자료를 확인하지 못했습니다."),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(actions))

    def unavailable(*args):
        raise ReconstructionUnavailable("fixture missing")

    monkeypatch.setattr(agent_runner, "execute_agent_tool", unavailable)
    client = TestClient(app)
    response = client.post("/api/agent/ask", json={"message": "연결 자료를 확인해줘"})
    assert response.status_code == 200
    diagnostics = response.json()["diagnostics"]
    assert [(failure["stage"], failure["code"]) for failure in diagnostics["failures"]] == [
        ("validation", "tool_input_rejected"), ("tool", "tool_execution_failed"),
    ]
    assert diagnostics["failures"][0]["tool_name"] is None
    follow = client.post("/api/agent/ask", json={"message": "무슨 질문을 할 수 있어?"}).json()["diagnostics"]
    assert follow["failures"] == [] and follow["model_steps"] == 0
    assert follow["completion_source"] == "capability"
    assert follow["request_id"] != diagnostics["request_id"]
    assert agent_runner._run_state.get() is None


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-2", "invalid"])
def test_timeout_configuration_rejects_unbounded_or_invalid_values(monkeypatch, value):
    monkeypatch.setenv("AGENT_ASK_TIMEOUT_SECONDS", value)
    assert agent_runner._ask_timeout_seconds() == 25.0

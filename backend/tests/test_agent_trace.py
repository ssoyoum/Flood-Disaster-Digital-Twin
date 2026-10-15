"""Per-request trace: step order, failure classes, token usage and the opt-in JSONL log."""

import json

import httpx
from fastapi.testclient import TestClient

from app import agent_runner
from app.main import app
from app.schemas import AgentAskRequest


def _scripted(monkeypatch, *actions):
    queue = iter(actions)
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(queue))


def test_trace_follows_router_model_validation_tool_answer_reply(monkeypatch):
    _scripted(monkeypatch,
              agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing",
                                       parameters={"closure_times": ["08:20"]}),
              agent_runner.AgentAction(action="final", answer="08:20 통제는 유입보다 7분 앞섭니다 [1].", evidence_calls=[1]))
    result = agent_runner.ask_agent(AgentAskRequest(message="08:20에 통제했다면?"))
    trace = result["diagnostics"]["trace"]
    assert [(step["stage"], step["outcome"]) for step in trace] == [
        ("router", "current"), ("model", "decision_tool"), ("validation", "accepted"), ("tool", "ok"),
        ("model", "decision_final"), ("answer", "grounded"), ("reply", "answered"),
    ]
    assert [step["seq"] for step in trace] == list(range(1, len(trace) + 1))
    assert trace[3]["tool_name"] == "analyze_closure_timing" and trace[3]["by"] == "model"
    assert trace[-1]["by"] == "model"
    # Same privacy rule as failures: no question text or parameter values in the trace.
    assert "08:20" not in json.dumps(trace)


def test_selection_input_and_repeat_errors_are_separate_codes(monkeypatch):
    _scripted(monkeypatch,
              agent_runner.AgentAction(action="tool", tool_name="analyze_alert_timing",
                                       parameters={"thresholds_mm_per_hour": [95]}),
              agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing",
                                       parameters={"closure_times": ["07:00"]}),
              agent_runner.AgentAction(action="tool", tool_name="get_event"),
              agent_runner.AgentAction(action="tool", tool_name="get_event"),
              agent_runner.AgentAction(action="final", gap_kind="outside_scope", answer="등록된 도구로 답할 수 없는 질문입니다."))
    diagnostics = agent_runner.ask_agent(AgentAskRequest(message="사건 정보를 알려줘"))["diagnostics"]
    assert [failure["code"] for failure in diagnostics["failures"]] == [
        "tool_selection_rejected", "tool_input_rejected", "tool_call_repeated",
    ]
    # Osong has no alert tool; the name is registered elsewhere, so it is still reported.
    assert diagnostics["failures"][0]["tool_name"] == "analyze_alert_timing"


def test_offline_hint_fallback_is_marked_as_server_run(monkeypatch):
    def unavailable(context):
        raise agent_runner.LlmPlannerUnavailable("offline")

    monkeypatch.setattr(agent_runner, "_gemini_action", unavailable)
    trace = agent_runner.ask_agent(AgentAskRequest(message="08:20에 통제했다면?"))["diagnostics"]["trace"]
    assert [(step["stage"], step["outcome"], step["by"]) for step in trace] == [
        ("router", "current", "server"), ("model", "model_unavailable", "model"),
        ("tool", "ok", "server"), ("reply", "answered", "registered_tools"),
    ]


def _decision_with_usage(decision, usage):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(decision)}]}}],
                                     "usageMetadata": usage})


def test_token_usage_is_summed_over_model_responses(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(agent_runner, "llm_planner_status", lambda: {"available": True})
    responses = iter([
        _decision_with_usage({"action": "tool", "tool_name": "get_event"},
                             {"promptTokenCount": 1000, "candidatesTokenCount": 40, "totalTokenCount": 1040}),
        _decision_with_usage({"action": "final", "answer": "등록된 사건 정보를 확인했습니다 [1].", "evidence_calls": [1]},
                             {"promptTokenCount": 1500, "candidatesTokenCount": 60, "thoughtsTokenCount": 5,
                              "totalTokenCount": 1565}),
    ])

    async def post(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(agent_runner, "_post_gemini", post)
    tokens = agent_runner.ask_agent(AgentAskRequest(message="사건 정보를 알려줘"))["diagnostics"]["tokens"]
    assert tokens == {"prompt": 2500, "output": 100, "thoughts": 5, "total": 2605, "responses": 2}


def test_tokens_are_null_without_a_model_response():
    result = agent_runner.ask_agent(AgentAskRequest(message="무슨 질문을 할 수 있어?"))
    assert result["diagnostics"]["tokens"] is None


def test_trace_log_matches_the_api_response_and_omits_question(monkeypatch, tmp_path):
    log = tmp_path / "agent-trace.jsonl"
    monkeypatch.setenv("FLOODOPS_AGENT_TRACE_LOG", str(log))

    def unavailable(context):
        raise agent_runner.LlmPlannerUnavailable("offline")

    monkeypatch.setattr(agent_runner, "_gemini_action", unavailable)
    body = TestClient(app).post("/api/agent/ask", json={"message": "유입을 10분 늦췄다면?"}).json()
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["diagnostics"]["request_id"] == body["diagnostics"]["request_id"]
    assert record["diagnostics"]["trace"] == body["diagnostics"]["trace"]
    assert [call["tool_name"] for call in record["tool_calls"]] == [call["tool_name"] for call in body["tool_calls"]]
    assert "유입을" not in lines[0] and "delay_minutes" not in lines[0]

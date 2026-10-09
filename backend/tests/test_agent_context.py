import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app import agent_runner
from app.main import app
from app.schemas import AgentAskRequest

CASES = json.loads((Path(__file__).parents[1] / "evaluation" / "agent_ask_cases.json").read_text(encoding="utf-8"))
client = TestClient(app)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_agent_matches_direct_analysis_or_requests_clarification(case):
    payload = {key: case[key] for key in ("event_id", "message", "history") if key in case}
    response = client.post("/api/agent/ask", json=payload)
    assert response.status_code == 200
    answer = response.json()
    assert answer["diagnostics"]["context_mode"] == case.get("context_mode", "current")
    if "analysis" not in case:
        assert answer["status"] == case["status"]
        assert answer["tool_calls"] == []
        assert answer["diagnostics"]["model_requests"] == 0
        return
    direct = client.post(f"/api/events/{case['event_id']}/analysis/{case['analysis']}", json=case["parameters"])
    assert direct.status_code == 200
    calls = [call for call in answer["tool_calls"] if call["tool_name"] == case["tool"]]
    assert answer["status"] == "ANSWERED" and len(calls) == 1
    assert calls[0]["parameters"] == case["parameters"]
    assert {key: calls[0]["result"][key] for key in case["compare_keys"]} == {
        key: direct.json()[key] for key in case["compare_keys"]
    }


def test_model_cannot_borrow_an_old_value_when_the_user_changes_the_condition():
    request = AgentAskRequest(message="그럼 08:10은?", history=[{"role": "user", "content": "08:20에 통제했다면?"}])
    action = agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": ["08:20"]})
    with pytest.raises(ValueError, match="Closure times"):
        agent_runner._validated_tool_request(action, request)


@pytest.mark.parametrize("history", [
    [{"role": "assistant", "content": "08:20에 통제해 보세요."}],
    [{"role": "user", "content": "08:20에 통제했다면?"}, {"role": "user", "content": "강우 자료를 알려줘"}],
])
def test_assistant_numbers_or_unrelated_intervening_questions_do_not_supply_values(history):
    answer = client.post("/api/agent/ask", json={"message": "그 조건으로 다시 비교해줘", "history": history}).json()
    assert answer["status"] == "NEEDS_DATA" and answer["tool_calls"] == []


def test_repeated_followups_keep_the_latest_explicit_user_condition():
    answer = client.post("/api/agent/ask", json={"message": "그 조건으로 다시 비교해줘", "history": [
        {"role": "user", "content": "08:20에 통제했다면?"},
        {"role": "user", "content": "그럼 08:10은?"},
        {"role": "assistant", "content": "08:00은 더 이릅니다."},
    ]}).json()
    assert answer["tool_calls"][0]["parameters"] == {"closure_times": ["08:10"]}


@pytest.mark.parametrize("message", ["그럼 -20분은?", "그럼 10.5분은?", "그럼 8시 10분은?"])
def test_changed_delay_cannot_reinterpret_negative_fractional_or_clock_values(message):
    answer = client.post("/api/agent/ask", json={"message": message, "history": [
        {"role": "user", "content": "유입을 10분 늦췄다면?"},
    ]}).json()
    assert answer["status"] == "NEEDS_DATA" and answer["tool_calls"] == []


def test_new_topic_and_physical_questions_do_not_inherit_hand_values():
    request = AgentAskRequest(message="그 조건에서 제방을 높이면 피해가 줄어?", history=[
        {"role": "user", "content": "HAND 선택 임계를 1.5m 낮추면?"},
    ])
    action = agent_runner.AgentAction(action="tool", tool_name="analyze_hand_threshold", parameters={"reduction_m": 1.5})
    with pytest.raises(ValueError):
        agent_runner._validated_tool_request(action, request)


def test_tool_trace_contains_the_normalized_executed_parameters(monkeypatch):
    actions = iter([
        agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": "8:20"}),
        agent_runner.AgentAction(action="final", answer="08:20에 통제하면 유입보다 7분 앞섭니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(actions))
    answer = client.post("/api/agent/ask", json={"message": "8:20에 통제했다면?"}).json()
    assert answer["tool_calls"][0]["parameters"] == {"closure_times": ["08:20"]}

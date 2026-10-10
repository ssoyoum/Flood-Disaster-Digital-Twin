from datetime import datetime

from fastapi.testclient import TestClient
import pytest

from app import agent_runner, agent_facility, twin
from app.main import app
from app.schemas import AgentAskRequest

client = TestClient(app)
FACILITY = "gungpyeong2-underpass"
SCOPE = {"event_id": "osong-2023", "facility_id": FACILITY, "observation_at": "2023-07-15T08:00:00"}


def ask(message, **scope):
    return client.post("/api/agent/ask", json={**SCOPE, **scope, "message": message})


def test_facility_catalog_and_examples_are_limited_to_three_registered_tools():
    params = {"facility_id": FACILITY}
    tools = client.get("/api/agent/tools", params=params).json()
    assert {tool["name"] for tool in tools} == agent_facility.TOOL_NAMES
    examples = client.get("/api/agent/examples", params=params).json()
    assert len(examples) == 3 and {item["workflow"] for item in examples} == {"facility_status", "control_rule", "facility_backtest"}


@pytest.mark.parametrize("question,tool", [
    ("선택 시설의 상태와 수위 여유를 설명해줘", "get_facility_status"),
    ("통제 검토 기준과 근거는 무엇인가요?", "get_control_rule"),
    ("과거 수위 백테스트는 어땠어?", "get_facility_backtest"),
])
def test_offline_facility_answers_include_tool_derived_explanations(question, tool):
    response = ask(question)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ANSWERED" and body["facility_id"] == FACILITY
    call = body["tool_calls"][0]
    assert call["tool_name"] == tool and call["parameters"]["observation_at"] == SCOPE["observation_at"]
    assert body["evidence_calls"] == [1] and "[1]" in body["answer"]
    assert "아래 결과 표를 확인" not in body["answer"]
    assert body["diagnostics"]["completion_source"] == "registered_tools"
    if tool == "get_facility_status":
        assert "과거 재생" in body["answer"]
        assert call["result"]["mode"] == "replay" and call["result"]["decision_usable"] is False
    if tool == "get_facility_backtest":
        direct = client.get(f"/api/twin/facilities/{FACILITY}/backtest").json()
        assert call["result"]["lead_minutes"] == direct["lead_minutes"]
        assert "06:40" in body["answer"] and "06:50" in body["answer"] and "DQ-009" in body["answer"]


def test_status_and_rule_are_both_returned_for_a_combined_question():
    body = ask("시설 상태와 통제 검토 기준을 함께 설명해줘").json()
    assert {call["tool_name"] for call in body["tool_calls"]} == {"get_facility_status", "get_control_rule"}
    assert body["evidence_calls"] == [1, 2]
    assert "과거 재생" in body["answer"] and "상승 속도 조건은 가정" in body["answer"]


@pytest.mark.parametrize("scope,code", [
    ({"facility_id": "no-such-facility"}, 404),
    ({"event_id": "seoul-2022"}, 422),
    ({"observation_at": "08:00"}, 422),
    ({"observation_at": "not-an-iso-time"}, 422),
    ({"facility_id": None}, 422),
])
def test_invalid_scope_is_rejected_before_a_model_request(monkeypatch, scope, code):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: pytest.fail("Invalid scope must not call Gemini"))
    assert ask("상태를 설명해줘", **scope).status_code == code


def test_model_cannot_switch_facility_time_or_borrow_historical_tools():
    request = AgentAskRequest(message="시설 상태", **SCOPE)
    for name, parameters in [
        ("get_facility_status", {"facility_id": "another-facility"}),
        ("get_facility_status", {"observation_at": "2023-07-15T03:00:00"}),
        ("analyze_closure_timing", {"closure_times": ["08:00"]}),
    ]:
        with pytest.raises(ValueError):
            agent_runner._validated_tool_request(agent_runner.AgentAction(action="tool", tool_name=name, parameters=parameters), request)


def test_missing_and_stale_observations_are_not_a_present_safety_verdict(monkeypatch):
    body = ask("시설 상태", observation_at="2024-01-01T08:00:00").json()
    assert body["status"] == "NEEDS_DATA" and "관측이 없어" in body["answer"]
    stale = twin.assess(twin.FACILITIES[FACILITY], [{"time": datetime(2023, 7, 15, 6, 50), "water_level_m": 9.38}], datetime(2023, 7, 15, 8, 0))
    monkeypatch.setattr(twin, "facility_status", lambda *args: {**stale, "mode": "live"})
    body = ask("현재 상태", observation_at=None).json()
    assert body["status"] == "NEEDS_DATA"
    assert body["tool_calls"][0]["result"]["observation_quality"] == "stale"
    assert "현재 통제 판단에 사용할 수 없습니다" in body["answer"]


def test_live_source_failure_does_not_leak_key_or_substitute_replay(monkeypatch):
    def unavailable(*args):
        raise RuntimeError("https://source.invalid/secret-api-key/observations")
    monkeypatch.setattr(twin, "facility_status", unavailable)
    body = ask("현재 상태와 통제 기준", observation_at=None).json()
    assert body["status"] == "NEEDS_DATA"
    assert "secret-api-key" not in str(body)
    assert [call["tool_name"] for call in body["tool_calls"]] == ["get_control_rule"]


@pytest.mark.parametrize("timestamp", ["2023-07-14T23:00:00+00:00", "2023-07-14T23:00:00Z"])
def test_explicit_replay_time_does_not_use_live_source(monkeypatch, timestamp):
    monkeypatch.setattr(twin, "facility_status", lambda *args: pytest.fail("Explicit replay must not query live"))
    body = ask("시설 상태", observation_at=timestamp).json()
    assert body["tool_calls"][0]["result"]["at"] == "2023-07-15T08:00:00"
    assert body["tool_calls"][0]["result"]["mode"] == "replay"


def test_unsafe_model_answer_is_replaced_with_cited_tool_explanation(monkeypatch):
    actions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_facility_status"),
        agent_runner.AgentAction(action="final", answer="현재 안전합니다. 통제를 실행했습니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(actions))
    body = ask("현재 시설 상태").json()
    assert "과거 재생" in body["answer"] and "통제를 실행했습니다" not in body["answer"]
    assert body["diagnostics"]["completion_source"] == "registered_tools"


def test_direct_tool_api_enforces_facility_scope():
    response = client.post("/api/agent/tools/analyze_hand_threshold", json=SCOPE)
    assert response.status_code == 404
    response = client.post("/api/agent/tools/get_facility_status", json={"event_id": "osong-2023"})
    assert response.status_code == 422


def test_model_backtest_answer_keeps_the_observation_time_discrepancy(monkeypatch):
    actions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_facility_backtest"),
        agent_runner.AgentAction(action="final", answer="과거 백테스트의 첫 권고는 05:50입니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(actions))
    body = ask("과거 백테스트").json()
    assert body["diagnostics"]["completion_source"] == "model"
    assert "06:40" in body["answer"] and "06:50" in body["answer"] and "DQ-009" in body["answer"]


def test_physical_effect_question_is_refused_without_a_model(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: pytest.fail("Facility physical effects are unavailable"))
    body = ask("제방을 1m 높였다면?").json()
    assert body["status"] == "NEEDS_DATA" and body["tool_calls"] == []
    assert len(body["follow_ups"]) == 3

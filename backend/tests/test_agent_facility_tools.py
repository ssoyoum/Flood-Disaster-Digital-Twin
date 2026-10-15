"""Criteria-review and research rise-model tools in the facility Agent scope."""

from fastapi.testclient import TestClient
import pytest

from app import agent_facility, agent_runner
from app.main import app

client = TestClient(app)
SCOPE = {"event_id": "osong-2023", "facility_id": "gungpyeong2-underpass", "observation_at": "2023-07-15T04:10:00"}


@pytest.fixture(autouse=True)
def replay(monkeypatch):
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")


@pytest.mark.parametrize("question,tool", [
    ("기준을 경보+120분으로 바꾸면 몇 분 먼저 검토하나요?", "get_criteria_review"),
    ("다른 해에도 권고가 나왔나요?", "get_criteria_review"),
    ("연구 모델은 6시간 안에 얼마나 오른다고 보나요?", "get_rise_forecast"),
])
def test_hints_route_to_the_new_tools(question, tool):
    assert tool in {hint["tool_name"] for hint in agent_facility.hints(question)}


def test_criteria_summary_lists_each_rule_once_and_does_not_judge_other_years(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: (_ for _ in ()).throw(agent_runner.LlmPlannerUnavailable("offline")))
    body = client.post("/api/agent/ask", json={**SCOPE, "message": "기준별로 다른 해 권고가 몇 번 나오는지 비교해줘"}).json()
    call = next(call for call in body["tool_calls"] if call["tool_name"] == "get_criteria_review")
    assert "sweep" in call["result"] and "step_reviews" not in str(call["result"].get("quality", ""))
    assert body["answer"].count("계획홍수위만") == 1
    assert "필요·불필요를 판단하지 않습니다" in body["answer"]


def test_model_answer_on_rise_without_research_label_is_replaced(monkeypatch):
    actions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_rise_forecast"),
        agent_runner.AgentAction(action="final", answer="6시간 안에 1.76m 오릅니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(actions))
    body = client.post("/api/agent/ask", json={**SCOPE, "message": "앞으로 6시간 얼마나 오를까?"}).json()
    assert body["diagnostics"]["completion_source"] == "registered_tools"
    assert "연구 모델" in body["answer"] and agent_facility.RESEARCH_CAVEAT in body["answer"]


def test_follow_ups_skip_tools_already_used_and_stay_at_three(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: (_ for _ in ()).throw(agent_runner.LlmPlannerUnavailable("offline")))
    body = client.post("/api/agent/ask", json={**SCOPE, "message": "연구 모델은 6시간 안에 얼마나 오른다고 보나요?"}).json()
    used = {call["tool_name"] for call in body["tool_calls"]}
    examples = {item["question"]: f"get_{item['workflow']}" for item in agent_facility.EXAMPLES}
    assert len(body["follow_ups"]) == 3
    assert not {examples[question] for question in body["follow_ups"]} & used


@pytest.mark.parametrize("question", ["과거 수위 백테스트에서 통제 검토는 언제 시작됐나요?", "기준별로 다른 해 권고가 몇 번 나오는지 비교해줘"])
def test_lead_time_answers_state_archive_data_current_levels_and_no_look_ahead(monkeypatch, question):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: (_ for _ in ()).throw(agent_runner.LlmPlannerUnavailable("offline")))
    body = client.post("/api/agent/ask", json={**SCOPE, "message": question}).json()
    answer = body["answer"]
    assert "2026년에 홍수통제소에서 다시 받은 보관 수위" in answer
    assert "경보 8.0 m·계획홍수위 9.38 m" in answer and "당시 기준값이 같았는지는 확인하지 않았습니다" in answer
    assert "직전 30분 수위만 써서 미래 값을 보지 않습니다" in answer
    assert answer.count(agent_facility.ARCHIVE_MARKER) == 1

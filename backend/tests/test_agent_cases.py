from fastapi.testclient import TestClient

from app import agent_runner
from app.llm_planner import LlmPlannerUnavailable
from app.main import app

client = TestClient(app)


def _ask(event_id: str, message: str):
    return client.post("/api/agent/ask", json={"event_id": event_id, "message": message}).json()


def _offline(_context):
    raise LlmPlannerUnavailable("offline in tests")


def test_examples_and_tools_follow_the_event():
    seoul = [item["question"] for item in client.get("/api/agent/examples", params={"event_id": "seoul-2022"}).json()]
    assert any("빗물터널" in question for question in seoul)
    osong = [item["question"] for item in client.get("/api/agent/examples").json()]
    assert any("지하차도" in question for question in osong)


def test_seoul_alert_question_runs_alert_timing_from_written_threshold(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", _offline)
    result = _ask("seoul-2022", "신림 강우계가 시간당 95mm를 넘었을 때 저지대 경보를 보냈다면 첫 구조 신고까지 몇 분이었나요?")
    call = result["tool_calls"][0]
    assert call["tool_name"] == "analyze_alert_timing"
    assert call["result"]["scenarios"][0]["minutes_before_first_rescue_call"] == 10


def test_seoul_tunnel_question_uses_the_registered_storage(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", _offline)
    result = _ask("seoul-2022", "신월 규모 저류시설이 도림천에 있었다면 얼마나 담았을까?")
    call = result["tool_calls"][0]
    assert call["tool_name"] == "analyze_storage_capture"
    assert call["result"]["storage_m3"] == 320000


def test_pohang_relative_time_resolves_against_the_actual_broadcast(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", _offline)
    result = _ask("pohang-2022", "진입 금지 안내를 30분 일찍 했다면 완전 침수까지 몇 분 남나요?")
    call = result["tool_calls"][0]
    assert call["parameters"] == {"intervention_id": "parking_entry_ban", "action_times": ["06:00"]}
    rows = {row["action_time"][11:16]: row for row in call["result"]["scenarios"]}
    assert rows["06:00"]["minutes_before_milestones"]["parking_full"] == 45


def test_andong_model_answer_is_grounded_and_flagged_as_press(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(
            action="tool", tool_name="analyze_response_timing",
            parameters={"intervention_id": "evacuation_order", "action_times": ["23:40"]}, reason="대피명령 시각 비교",
        ),
        agent_runner.AgentAction(
            action="final", answer="23:40에 대피명령을 냈다면 경보 수위 도달 예측까지 50분이 있었습니다 [1].", evidence_calls=[1],
        ),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))
    result = _ask("andong-uiseong-2026", "23:40 홍수경보 때 바로 대피명령을 냈다면?")
    assert result["status"] == "ANSWERED"
    assert "50분" in result["answer"] and "언론 보도" in result["answer"]


def test_model_cannot_invent_case_values_or_borrow_osong_tools(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="analyze_response_timing",
                                 parameters={"intervention_id": "evacuation_order", "action_times": ["21:00"]}),
        agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": ["23:40"]}),
        # The runner anchors a what-if on the timeline once, then asks again.
        *[agent_runner.AgentAction(action="final", gap_kind="missing_parameter", answer="몇 시에 대피명령을 냈다고 가정할지 알려 주세요.")] * 2,
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))
    result = _ask("andong-uiseong-2026", "대피명령을 더 빨리 냈다면 어땠을까?")
    assert [call["tool_name"] for call in result["tool_calls"]] == ["get_reconstruction"]
    assert any("Action times" in item for item in result["limitations"])
    assert any("not registered for this event" in item for item in result["limitations"])


def test_capability_answer_lists_the_event_questions():
    result = _ask("pohang-2022", "무슨 질문을 할 수 있어?")
    assert "지하주차장" in result["answer"] and "지하차도" not in result["answer"]

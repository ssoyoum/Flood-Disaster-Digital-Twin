from fastapi.testclient import TestClient

from app import agent_runner
from app.main import app

client = TestClient(app)


def _ask(message: str):
    return client.post("/api/agent/ask", json={"event_id": "osong-2023", "message": message})


def test_physical_question_cites_timeline_and_keeps_the_model_explanation(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_reconstruction", reason="월류·붕괴 시각 확인"),
        agent_runner.AgentAction(
            action="final",
            answer="제방을 3m 올린 효과 자체는 계산할 수 없습니다. 기록상 월류는 07:50, 임시제방 붕괴는 08:09입니다 [1].",
            evidence_calls=[1],
            follow_ups=["유입이 30분 늦춰졌다면 주행불능 시각은 언제인가요?", "08:00에 통제했다면 유입까지 몇 분 여유가 있었나요?"],
        ),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))
    result = _ask("제방을 3미터 올린다면?").json()
    assert result["status"] == "NEEDS_DATA"
    assert "07:50" in result["answer"] and "08:09" in result["answer"]
    assert "수리모형" in result["answer"]
    assert [call["tool_name"] for call in result["tool_calls"]] == ["get_reconstruction"]
    assert result["follow_ups"][0].startswith("유입이 30분")


def test_uncited_gap_answer_is_kept_when_it_adds_no_numbers(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: agent_runner.AgentAction(
        action="final", gap_kind="outside_scope",
        answer="강우량이 달라졌을 때의 침수 변화는 강우-유출 모형이 없어 계산할 수 없습니다.",
        follow_ups=["유입이 20분 늦춰졌다면 어떻게 되나요?"],
    ))
    result = _ask("비가 절반만 왔다면 어땠을까?").json()
    assert result["status"] == "NEEDS_DATA"
    assert result["answer"].startswith("강우량이 달라졌을 때")
    assert result["follow_ups"] == ["유입이 20분 늦춰졌다면 어떻게 되나요?"]


def test_uncited_gap_answer_with_invented_numbers_falls_back(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: agent_runner.AgentAction(
        action="final", gap_kind="physical_intervention",
        answer="제방을 3m 올리면 침수가 40% 줄어듭니다.",
    ))
    result = _ask("제방을 3미터 올린다면?").json()
    assert "40%" not in result["answer"]
    assert "수리모형" in result["answer"]
    assert 1 <= len(result["follow_ups"]) <= 3


def test_observation_summary_tool_returns_observed_peaks():
    tools = [tool["name"] for tool in client.get("/api/agent/tools").json()]
    assert "get_observation_summary" in tools
    result = client.post("/api/agent/tools/get_observation_summary", json={"event_id": "osong-2023"}).json()["result"]
    assert result["rainfall_peak_mm_per_hour"] == 32.5
    assert result["water_level_peak_station_name"] == "청주시(미호강교)"


def test_named_milestone_time_can_be_used_after_the_timeline_is_read(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_reconstruction"),
        agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": ["04:10"]}),
        agent_runner.AgentAction(action="final", answer="홍수경보 시각인 04:10에 통제했다면 유입보다 257분 앞섭니다 [2].", evidence_calls=[2]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))
    result = _ask("경보 나오자마자 통제했으면 어땠을까?").json()
    assert [call["tool_name"] for call in result["tool_calls"]] == ["get_reconstruction", "analyze_closure_timing"]
    assert result["tool_calls"][1]["result"]["scenarios"][0]["minutes_before_underpass_inflow"] == 257


def test_invented_time_is_still_rejected_without_a_matching_milestone(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_reconstruction"),
        agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": ["07:33"]}),
        agent_runner.AgentAction(action="final", gap_kind="missing_parameter", answer="통제 시각을 알려 주세요."),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))
    result = _ask("좀 더 일찍 막았으면?").json()
    assert "analyze_closure_timing" not in [call["tool_name"] for call in result["tool_calls"]]


def test_supported_delay_question_runs_the_tool_even_if_the_model_declines(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="final", gap_kind="outside_scope", answer="지연 시뮬레이션 기능이 없어 계산할 수 없습니다."),
        agent_runner.AgentAction(action="final", answer="유입이 10분 늦춰지면 주행불능은 08:45입니다 [1].", evidence_calls=[1]),
    ])
    contexts = []

    def decide(context):
        contexts.append(context)
        return next(decisions)

    monkeypatch.setattr(agent_runner, "_gemini_action", decide)
    result = _ask("유입이 10분 늦춰졌다면 주행불능 시각은 언제인가요?").json()
    assert contexts[0]["suggested_tools"][0] == {"tool_name": "analyze_inflow_delay", "parameters": {"delay_minutes": [10]}}
    assert [call["tool_name"] for call in result["tool_calls"]] == ["analyze_inflow_delay"]
    assert result["status"] == "ANSWERED"
    assert "08:45" in result["answer"]


def test_tools_named_in_the_question_still_run_when_gemini_is_unavailable():
    # conftest removes GEMINI_API_KEY, so the planner reports itself unavailable.
    result = _ask("유입이 10분 늦춰졌다면 주행불능 시각은 언제인가요?").json()
    assert result["status"] == "ANSWERED"
    assert [call["tool_name"] for call in result["tool_calls"]] == ["analyze_inflow_delay"]
    assert result["tool_calls"][0]["parameters"] == {"delay_minutes": [10]}
    assert any("No Gemini" in item or "credential" in item.lower() for item in result["limitations"])


def test_model_number_formats_are_normalised_before_validation(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="analyze_inflow_delay", parameters={"delay_minutes": [10.0]}),
        agent_runner.AgentAction(action="final", answer="유입이 10분 늦춰지면 주행불능은 08:45입니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))
    result = _ask("유입이 10분 늦춰졌다면 주행불능 시각은 언제인가요?").json()
    assert result["status"] == "ANSWERED"
    assert result["tool_calls"][0]["tool_name"] == "analyze_inflow_delay"


def test_relative_closure_phrase_resolves_against_the_registered_baseline(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": ["08:17"]}),
        agent_runner.AgentAction(action="final", answer="기준 통제 시각 08:27보다 10분 이른 08:17에 차단하면 유입보다 10분 앞섭니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))
    result = _ask("차단을 10분 일찍한다면?").json()
    assert result["status"] == "ANSWERED"
    assert result["tool_calls"][0]["parameters"]["closure_times"] == ["08:17"]
    assert result["tool_calls"][0]["result"]["scenarios"][0]["minutes_before_underpass_inflow"] == 10

"""Week-2 stability fixes found by the benchmark baseline (docs/AGENT_EVALUATION_RESULTS.md)."""

from app import agent_runner
from app.agent_cases import run_tool
from app.schemas import AgentAskRequest, AgentToolCallRequest
from app.services import ReconstructionUnavailable


def _scripted(monkeypatch, *actions):
    queue = iter(actions)
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(queue))


def _outage(monkeypatch):
    def unavailable(context):
        raise agent_runner.LlmPlannerUnavailable("offline")

    monkeypatch.setattr(agent_runner, "_gemini_action", unavailable)


def test_thousands_separators_match_tool_json_but_invented_values_do_not():
    calls = [{"order": 1, "tool_name": "analyze_storage_capture", "result": {"excess_volume_m3": 1242453, "captured_volume_m3": 400000}}]
    assert agent_runner._grounded_answer("초과 부피 1,242,453 ㎥ 중 400,000 ㎥를 담습니다 [1].", calls, [1])
    assert not agent_runner._grounded_answer("초과 부피 1,242,454 ㎥입니다 [1].", calls, [1])
    assert agent_runner._numbers("08:20, 95, 1,000.5") == {"08:20", "95", "1000.5"}


def test_storage_result_carries_the_rescue_call_its_minutes_count_to():
    result = run_tool("analyze_storage_capture", "seoul-2022", AgentToolCallRequest(event_id="seoul-2022", storage_m3=400000))
    assert result["first_rescue_call"].startswith("2022-08-08T20:59")
    assert result["storage_full_minutes_before_first_rescue_call"] is not None


def test_retrying_a_failed_tool_stops_the_loop(monkeypatch):
    closure = agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": ["08:20"]})
    _scripted(monkeypatch, closure, closure, closure, closure, closure, closure)

    def broken(*args):
        raise ReconstructionUnavailable("fixture missing")

    monkeypatch.setattr(agent_runner, "execute_agent_tool", broken)
    result = agent_runner.ask_agent(AgentAskRequest(message="08:20에 통제했다면?"))
    diagnostics = result["diagnostics"]
    assert diagnostics["model_steps"] == 2
    assert [failure["code"] for failure in diagnostics["failures"]] == ["tool_execution_failed", "tool_call_repeated"]
    assert result["status"] == "NEEDS_DATA" and not result["tool_calls"]
    assert "The Agent stopped after repeated tool calls." in result["limitations"]


def test_repeating_a_successful_call_points_back_to_it_then_stops(monkeypatch):
    event = agent_runner.AgentAction(action="tool", tool_name="get_event")
    seen_contexts = []
    queue = iter([event, event, event, event])

    def decide(context):
        seen_contexts.append([dict(item) for item in context["observations"]])
        return next(queue)

    monkeypatch.setattr(agent_runner, "_gemini_action", decide)
    result = agent_runner.ask_agent(AgentAskRequest(message="사건 정보를 알려줘"))
    assert result["diagnostics"]["model_steps"] == 3
    assert [call["tool_name"] for call in result["tool_calls"]] == ["get_event"]
    assert "already made as [1]" in seen_contexts[2][-1]["error"]


def test_outage_still_refuses_physical_effects_without_running_tools(monkeypatch):
    _outage(monkeypatch)
    result = agent_runner.ask_agent(AgentAskRequest(message="제방을 1m 높였다면 침수가 줄었을까?"))
    assert result["status"] == "NEEDS_DATA" and not result["tool_calls"]
    assert result["diagnostics"]["completion_source"] == "clarification"
    assert "수리모형" in result["answer"]


def test_outage_does_not_answer_a_forecast_with_past_observations(monkeypatch):
    _outage(monkeypatch)
    result = agent_runner.ask_agent(AgentAskRequest(message="내일 비가 오면 어디가 잠겨?"))
    assert result["status"] == "NEEDS_DATA" and not result["tool_calls"]
    assert "예측하는 도구는 연결돼 있지 않습니다" in result["answer"]


def test_past_alert_wording_is_not_mistaken_for_a_forecast():
    assert not agent_runner._is_forecast_question("23:40 홍수경보 때 바로 대피명령을 냈다면 경보 수위 도달 예측까지 몇 분이었나요?")


def test_what_if_answered_only_from_recorded_times_is_not_marked_answered(monkeypatch):
    _scripted(monkeypatch,
              agent_runner.AgentAction(action="tool", tool_name="get_reconstruction"),
              agent_runner.AgentAction(action="final", answer="통제 시각이 주어지지 않아 효과를 계산하지 않았습니다. 기록된 유입은 사건 재구성에 있습니다 [1].",
                                       evidence_calls=[1]))
    result = agent_runner.ask_agent(AgentAskRequest(message="통제를 더 일찍 했다면?"))
    assert result["status"] == "NEEDS_DATA"
    assert "No analysis tool computed the assumed change; only recorded facts were cited." in result["limitations"]


def test_failed_analysis_is_not_recomputed_by_the_model_from_the_timeline(monkeypatch):
    _scripted(monkeypatch,
              agent_runner.AgentAction(action="tool", tool_name="analyze_closure_timing", parameters={"closure_times": ["08:20"]}),
              agent_runner.AgentAction(action="final", answer="08:20 통제는 유입 08:27보다 7분 앞섭니다 [1].", evidence_calls=[1]))
    real = agent_runner.execute_agent_tool

    def closure_broken(name, event_id, request):
        if name == "analyze_closure_timing":
            raise ReconstructionUnavailable("fixture missing")
        return real(name, event_id, request)

    monkeypatch.setattr(agent_runner, "execute_agent_tool", closure_broken)
    result = agent_runner.ask_agent(AgentAskRequest(message="08:20에 통제했다면?"))
    assert result["status"] == "NEEDS_DATA" and "7분" not in result["answer"]
    assert "대신 계산하지 않았습니다" in result["answer"]
    assert result["diagnostics"]["trace"][-2]["outcome"] == "analysis_tool_failed"


def test_model_timeout_after_rejected_what_if_does_not_report_answered(monkeypatch):
    calls = iter([
        agent_runner.AgentAction(action="tool", tool_name="analyze_inflow_delay", parameters={"delay_minutes": [500]}),
        agent_runner.AgentAction(action="final", answer="유입 지연을 계산할 수 없습니다."),
    ])

    def decide(context):
        action = next(calls, None)
        if action is None:
            raise agent_runner.LlmPlannerUnavailable("timed out")
        return action

    monkeypatch.setattr(agent_runner, "_gemini_action", decide)
    result = agent_runner.ask_agent(AgentAskRequest(message="유입을 500분 늦췄다면?"))
    assert [call["tool_name"] for call in result["tool_calls"]] == ["get_reconstruction"]
    assert result["status"] == "NEEDS_DATA"
    assert result["diagnostics"]["completion_source"] == "registered_tools"


def test_forecast_refusal_without_gap_kind_is_still_needs_data(monkeypatch):
    _scripted(monkeypatch,
              agent_runner.AgentAction(action="tool", tool_name="get_observation_summary"),
              agent_runner.AgentAction(action="final", answer="미래 강우에 따른 침수 지역 예측은 제공하지 않으며 기록된 관측만 확인할 수 있습니다 [1].",
                                       evidence_calls=[1]))
    result = agent_runner.ask_agent(AgentAskRequest(message="내일 비가 오면 어디가 잠겨?"))
    assert result["status"] == "NEEDS_DATA"
    assert "No registered tool forecasts future rainfall or flooding." in result["limitations"]


def test_ungrounded_prose_with_the_needed_tool_shows_results_as_answered(monkeypatch):
    _scripted(monkeypatch,
              agent_runner.AgentAction(action="tool", tool_name="get_observation_summary"),
              agent_runner.AgentAction(action="final", answer="그날 비는 999mm 왔습니다 [1].", evidence_calls=[1]))
    result = agent_runner.ask_agent(AgentAskRequest(message="그날 비는 얼마나 왔어?"))
    assert result["status"] == "ANSWERED" and result["diagnostics"]["completion_source"] == "registered_tools"
    assert "999" not in result["answer"]


def test_ungrounded_prose_without_a_tool_for_the_question_stays_needs_data(monkeypatch):
    _scripted(monkeypatch,
              agent_runner.AgentAction(action="tool", tool_name="get_reconstruction"),
              agent_runner.AgentAction(action="final", answer="침수심은 47.61m였습니다 [1].", evidence_calls=[1]))
    result = agent_runner.ask_agent(AgentAskRequest(message="궁평2지하차도 침수심은 몇 m였어?"))
    assert result["status"] == "NEEDS_DATA" and "47.61" not in result["answer"]


def test_model_timeout_on_a_forecast_question_is_not_answered(monkeypatch):
    actions = iter([agent_runner.AgentAction(action="tool", tool_name="get_observation_summary")])

    def decide(context):
        action = next(actions, None)
        if action is None:
            raise agent_runner.LlmPlannerUnavailable("timed out")
        return action

    monkeypatch.setattr(agent_runner, "_gemini_action", decide)
    result = agent_runner.ask_agent(AgentAskRequest(message="내일 비가 오면 어디가 잠겨?"))
    assert result["status"] == "NEEDS_DATA"


def test_loop_stalled_on_repeats_still_shows_the_needed_result(monkeypatch):
    rain = agent_runner.AgentAction(action="tool", tool_name="get_observation_summary")
    _scripted(monkeypatch, rain, rain, rain, rain)
    result = agent_runner.ask_agent(AgentAskRequest(message="그날 비는 얼마나 왔어?"))
    assert [call["tool_name"] for call in result["tool_calls"]] == ["get_observation_summary"]
    assert result["status"] == "ANSWERED" and result["diagnostics"]["completion_source"] == "registered_tools"

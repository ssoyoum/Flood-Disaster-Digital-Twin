"""Week-3 context trimming: the model reads less, the grounding check still sees everything."""

from app import agent_runner
from app.schemas import AgentAskRequest


def test_reconstruction_map_fields_reach_the_trace_but_not_the_model(monkeypatch):
    contexts = []
    actions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_reconstruction"),
        agent_runner.AgentAction(action="final", answer="지하차도 유입은 기록된 사건 시각에 있습니다 [1].", evidence_calls=[1]),
    ])

    def decide(context):
        contexts.append(context["observations"][:])
        return next(actions)

    monkeypatch.setattr(agent_runner, "_gemini_action", decide)
    result = agent_runner.ask_agent(AgentAskRequest(message="그날 경과를 시간순으로 알려줘"))
    seen = contexts[1][0]["result"]
    assert "envelope_comparison" not in seen and "replay" in seen and "intervention" in seen
    assert "envelope_comparison" in result["tool_calls"][0]["result"]

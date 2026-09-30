"""Capability questions should receive useful guidance without a tool call."""

import pytest

from app import agent_runner
from app.schemas import AgentAskRequest


@pytest.mark.parametrize("question", [
    "그럼 무슨 질문 할수있어?",
    "어떤 질문을 할 수 있나요?",
    "What can I ask?",
])
def test_capability_question_uses_registered_examples_without_gemini(monkeypatch, question):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: pytest.fail("Help should not call Gemini"))
    result = agent_runner.ask_agent(AgentAskRequest(message=question))

    assert result["status"] == "ANSWERED"
    assert result["tool_calls"] == []
    assert result["model"] is None
    assert "HAND 선택 임계" in result["answer"]
    assert "08:25에 지하차도를 통제" in result["answer"]
    assert "실제 침수 위험도 점수" in result["answer"]


def test_unknown_question_suggests_concrete_next_questions(monkeypatch):
    monkeypatch.setattr(
        agent_runner,
        "_gemini_action",
        lambda _context: agent_runner.AgentAction(action="final", answer="No tool data."),
    )
    result = agent_runner.ask_agent(AgentAskRequest(message="내일의 피해액을 예측해 줘"))

    assert result["status"] == "NEEDS_DATA"
    assert "08:25에 지하차도를 통제" in result["answer"]
    assert "No registered tool result" not in str(result)

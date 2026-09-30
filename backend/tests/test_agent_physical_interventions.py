"""Physical changes must not be reported as calculated HAND or flood effects."""

from fastapi.testclient import TestClient

from app import agent_runner
from app.main import app


client = TestClient(app)


def test_levee_height_question_explains_missing_physical_model(monkeypatch):
    monkeypatch.setattr(
        agent_runner,
        "_gemini_action",
        lambda _context: agent_runner.AgentAction(
            action="final",
            answer="제방 효과를 계산할 수 없습니다.",
        ),
    )

    response = client.post("/api/agent/ask", json={"message": "제방을 3미터 올린다면?"})

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "NEEDS_DATA"
    # Only the real timeline may be fetched; no analysis tool stands in for the levee change.
    assert [call["tool_name"] for call in result["tool_calls"]] in ([], ["get_reconstruction"])
    assert "제방" in result["answer"]
    assert "수리모형" in result["answer"]
    assert "HAND" in result["answer"]
    assert "사건·시각" not in result["answer"]


def test_levee_height_cannot_be_substituted_for_hand_threshold(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="analyze_hand_threshold", parameters={"reduction_m": 1.5}),
        agent_runner.AgentAction(action="final", gap_kind="physical_intervention"),
        agent_runner.AgentAction(action="final", gap_kind="physical_intervention"),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))

    response = client.post("/api/agent/ask", json={"message": "제방을 1.5미터 올린다면?"})

    result = response.json()
    assert result["status"] == "NEEDS_DATA"
    assert "analyze_hand_threshold" not in [call["tool_name"] for call in result["tool_calls"]]
    assert any("cannot be converted" in reason for reason in result["limitations"])


def test_event_citation_cannot_support_unmodelled_levee_effect(monkeypatch):
    decisions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_event"),
        agent_runner.AgentAction(action="final", answer="제방 증고로 침수가 줄어듭니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda _context: next(decisions))

    response = client.post("/api/agent/ask", json={"message": "제방을 3미터 올린다면?"})

    result = response.json()
    assert result["status"] == "NEEDS_DATA"
    assert result["tool_calls"][0]["tool_name"] == "get_event"
    assert "침수가 줄어듭니다" not in result["answer"]

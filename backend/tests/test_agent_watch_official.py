"""Watch-board Agent: official flood forecasts and validation cases."""

from fastapi.testclient import TestClient
import pytest

from app import agent_runner, agent_watch
from app.main import app

client = TestClient(app)
AT = "2023-07-15T06:00:00"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: (_ for _ in ()).throw(agent_runner.LlmPlannerUnavailable("offline")))


@pytest.mark.parametrize("question,tool,params", [
    ("지금 홍수특보 내려진 곳 있어?", "get_official_forecasts", {}),
    ("충북에 홍수경보 발령된 곳 알려줘", "get_official_forecasts", {"region": "충북"}),
    ("대전 사례에서 규칙이 실제 통제보다 빨랐어?", "validation_cases", {"region": "대전"}),
    ("검증 사례 보여줘", "validation_cases", {}),
])
def test_hints_route_official_and_validation_questions(question, tool, params):
    hint = agent_watch.hints(question)[0]
    assert hint["tool_name"] == tool and hint["parameters"] == params
    assert agent_watch.validate(tool, hint["parameters"], question) == params


def test_stage_questions_still_go_to_the_overview():
    assert agent_watch.hints("지금 전국에서 주의보 이상인 관측소가 몇 곳이야?")[0]["tool_name"] == "get_watch_overview"


def test_official_forecasts_answer_in_replay():
    body = client.post("/api/agent/ask", json={"board": "watch", "message": "충북에 홍수경보 발령된 곳 알려줘", "observation_at": AT}).json()
    call = body["tool_calls"][0]
    assert call["tool_name"] == "get_official_forecasts" and call["result"]["mode"] == "replay"
    assert all(row["region"] == "충북" for row in call["result"]["active"]) and call["result"]["counts"]["warning"] >= 2
    assert "미호천교" in body["answer"] or "미호강교" in body["answer"]


def test_validation_cases_answer_reports_the_late_2023_rule():
    body = client.post("/api/agent/ask", json={"board": "watch", "message": "대전 사례에서 규칙이 실제 통제보다 빨랐어?", "observation_at": AT}).json()
    result = body["tool_calls"][0]["result"]
    assert [c["id"] for c in result["cases"]] == ["daejeon-2020-07-30", "daejeon-2023-07-14", "daejeon-2024-07-10"]
    assert "늦음" in body["answer"] and "보도 기준" in body["answer"]

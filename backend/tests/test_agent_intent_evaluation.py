import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent_tools import plan_agent_intent
from app.schemas import AgentIntentPlanRequest


CASES = json.loads((Path(__file__).parent / "agent_intent_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_korean_intent_evaluation_case_matches_expected_plan(case):
    request = AgentIntentPlanRequest(
        event_id="osong-2023",
        message=case["message"],
        planner="deterministic",
    )

    actual = plan_agent_intent(request)

    assert actual["status"] == case["status"]
    assert actual.get("workflow") == case["workflow"]
    assert actual["parameters"] == case["parameters"]
    assert actual["tool_names"] == case["tool_names"]

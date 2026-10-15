"""Deterministic prompt size per benchmark question, with and without the week-3 trims.

A scripted model calls each case's expected tools once and then finishes, so every run sends
the same requests. The size counted is exactly what a provider receives per decision:
system prompt plus the JSON context. No model is called.
"""

import argparse
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("FLOODOPS_TWIN_MODE", "replay")

from app import agent_runner
from app.schemas import AgentAskRequest

CASES = Path(__file__).with_name("agent_benchmark_cases.json")
FULL_CATALOGUE = ("name", "description", "input_fields", "output", "use_when", "parameters", "can_say", "cannot_say", "examples")
VARIANTS = {
    "before": {"_MODEL_HIDDEN_FIELDS": {}, "_MODEL_CATALOGUE_FIELDS": FULL_CATALOGUE},
    "o1": {"_MODEL_CATALOGUE_FIELDS": FULL_CATALOGUE},
    "o1_o2": {},
}


def measure(case, variant):
    tools = list(case["expect"].get("tools", {}).items()) or [("get_facility_status" if case.get("facility_id") else "get_reconstruction", {})]
    script = iter([agent_runner.AgentAction(action="tool", tool_name=name, parameters=params) for name, params in tools]
                  + [agent_runner.AgentAction(action="final", answer="등록 도구 결과를 확인했습니다 [1].", evidence_calls=[1])] * 3)
    sizes = []

    def decide(context):
        sizes.append(len(agent_runner._system_prompt(context)) + len(json.dumps(context, ensure_ascii=False, default=str)))
        return next(script)

    request = AgentAskRequest(**{key: case[key] for key in ("event_id", "message", "history", "facility_id", "observation_at") if key in case})
    with patch.multiple(agent_runner, _model_action=decide, **VARIANTS[variant]):
        agent_runner.ask_agent(request)
    return sizes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for case in json.loads(CASES.read_text(encoding="utf-8")):
        if case["expect"].get("http", 200) != 200 or case.get("fail_tool"):
            continue
        try:
            row = {"case_id": case["id"], "category": case["category"], **{name: measure(case, name) for name in VARIANTS}}
        except Exception as exc:  # a scripted path the server rejects is reported, not hidden
            row = {"case_id": case["id"], "error": type(exc).__name__}
        rows.append(row)
    measured = [row for row in rows if "error" not in row and row["before"]]
    totals = {name: sum(sum(row[name]) for row in measured) for name in VARIANTS}
    summary = {"cases": len(measured), "chars_per_question": {name: round(total / len(measured)) for name, total in totals.items()},
               "change_vs_before_pct": {name: round(100 * (total - totals["before"]) / totals["before"], 1) for name, total in totals.items()},
               "first_request_chars": {name: round(sum(row[name][0] for row in measured) / len(measured)) for name in VARIANTS}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Compare local Agent answers with direct APIs; live mode explicitly uses Gemini."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.llm_planner import LlmPlannerUnavailable, llm_planner_status
from app.main import app
from app.rate_limit import agent_limiter


def evaluate(case, client):
    payload = {key: case[key] for key in ("event_id", "message", "history", "facility_id", "observation_at") if key in case}
    response = client.post("/api/agent/ask", json=payload)
    body = response.json()
    diagnostics = body.get("diagnostics") or {}
    checks = {"http_ok": response.status_code == 200,
              "event_matches": body.get("event_id") == case["event_id"],
              "context_matches": diagnostics.get("context_mode") == case.get("context_mode", "current")}
    if "facility_id" in case:
        checks["facility_matches"] = body.get("facility_id") == case["facility_id"]
    if "analysis" in case or "direct_path" in case:
        path = case.get("direct_path") or f"/api/events/{case['event_id']}/analysis/{case['analysis']}"
        direct = (client.get(path, params=case.get("direct_parameters", {})) if case.get("direct_method") == "GET" else
                  client.post(path, json=case.get("direct_parameters", case["parameters"])))
        calls = [call for call in body.get("tool_calls", []) if call["tool_name"] == case["tool"]]
        checks.update({"direct_http_ok": direct.status_code == 200,
                       "answered": body.get("status") == "ANSWERED",
                       "tool_matches": len(calls) == 1 and
                       {key: value for key, value in calls[0]["parameters"].items() if key != "event_id"} == case["parameters"] and
                       calls[0]["parameters"].get("event_id", case["event_id"]) == case["event_id"]})
        expected = direct.json()
        if case.get("direct_result_key"):
            expected = expected.get(case["direct_result_key"], {})
        checks["results_match"] = len(calls) == 1 and all(
            key in expected and key in calls[0]["result"] and calls[0]["result"][key] == expected[key]
            for key in case["compare_keys"])
    else:
        checks["clarified"] = body.get("status") == case["status"] and not body.get("tool_calls")
        checks["no_model_request"] = diagnostics.get("model_requests") == 0
    return {"case_id": case["id"], "passed": all(checks.values()), "checks": checks,
            "status": body.get("status"), "model": body.get("model"), "diagnostics": diagnostics,
            "answer": body.get("answer"), "context_note": body.get("context_note"),
            "tool_inputs": [{"tool_name": call["tool_name"], "parameters": call["parameters"]}
                            for call in body.get("tool_calls", [])]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline", "live"), default="offline",
                        help="live sends questions/history/tool outputs to configured Gemini and uses its quota")
    parser.add_argument("--case", action="append", default=[], help="case ID; repeat to select multiple")
    parser.add_argument("--suite", choices=("historical", "facility"), default="historical")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, required=True, help="save detailed answers locally, e.g. docs/local/agent-eval.json")
    args = parser.parse_args()
    fixture = "agent_facility_cases.json" if args.suite == "facility" else "agent_ask_cases.json"
    cases = json.loads(Path(__file__).with_name(fixture).read_text(encoding="utf-8"))
    unknown = set(args.case) - {case["id"] for case in cases}
    if unknown or (args.limit is not None and args.limit <= 0):
        parser.error(f"Invalid case IDs or limit: {sorted(unknown)}")
    if args.case:
        cases = [case for case in cases if case["id"] in args.case]
    if args.limit is not None:
        cases = cases[:args.limit]
    if args.mode == "live" and not llm_planner_status()["available"]:
        print("Live evaluation unavailable: configure the Gemini credential/model on this server.")
        return 2
    context = patch("app.agent_runner._gemini_action", side_effect=LlmPlannerUnavailable("offline evaluation")) if args.mode == "offline" else nullcontext()
    rows = []
    # Offline evaluation is an isolated local process and must not be mistaken
    # for public demo traffic. Live mode keeps the configured rate limits.
    limits = patch.dict(os.environ, {"FLOODOPS_AGENT_PER_MINUTE": "1000", "FLOODOPS_AGENT_PER_DAY": "1000",
                                    "FLOODOPS_AGENT_GLOBAL_PER_DAY": "1000"}) if args.mode == "offline" else nullcontext()
    observation_mode = patch.dict(os.environ, {"FLOODOPS_TWIN_MODE": "replay"}) if args.suite == "facility" else nullcontext()
    with limits, observation_mode, context, TestClient(app) as client:
        agent_limiter.reset()
        for case in cases:
            print(f"Evaluating {case['id']} ({args.mode})", flush=True)
            row = evaluate(case, client)
            rows.append(row)
            print(json.dumps({"case_id": row["case_id"], "passed": row["passed"],
                              "completion_source": row["diagnostics"].get("completion_source")}), flush=True)
    sources = {source: sum(row["diagnostics"].get("completion_source") == source for row in rows)
               for source in ("model", "registered_tools", "clarification", "unavailable", "capability")}
    summary = {"mode": args.mode, "suite": args.suite, "observation_mode": "replay" if args.suite == "facility" else None,
               "cases": len(rows), "passed": sum(row["passed"] for row in rows),
               "completion_sources": sources,
               "model_requests": sum(row["diagnostics"].get("model_requests", 0) for row in rows),
               "note": "Checks cover API values and routing; read actual answers to assess meaning and causal claims."}
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "summary": summary, "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary["passed"] == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

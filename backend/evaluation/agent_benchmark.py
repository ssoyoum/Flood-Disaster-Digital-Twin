"""Fixed Agent benchmark: behaviour checks plus quality, cost and latency metrics.

offline skips cases marked needs_model and replaces Gemini with an outage, so it
measures the server's own routing, refusals and fallbacks. live sends every case
to the configured Gemini model and uses its quota.
"""

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import agent_runner
from app.llm_planner import LlmPlannerUnavailable
from app.main import app
from app.rate_limit import agent_limiter
from app.services import ReconstructionUnavailable

CASES = Path(__file__).with_name("agent_benchmark_cases.json")
CATEGORIES = ("normal", "tool_selection", "ambiguous", "missing_data", "invalid_input", "tool_failure", "safe_wording")
_SCOPE_KEYS = {"event_id", "facility_id", "observation_at"}


def _failing_tool(name):
    real = agent_runner.execute_agent_tool

    def execute(tool_name, event_id, request):
        if tool_name == name:
            raise ReconstructionUnavailable("benchmark injected tool failure")
        return real(tool_name, event_id, request)

    return patch("app.agent_runner.execute_agent_tool", execute)


def _user_text(case):
    return " ".join([case["message"], *(turn["content"] for turn in case.get("history", []) if turn["role"] == "user")])


def _unsupported_numbers(answer, calls, case):
    evidence = json.dumps([call["result"] for call in calls], ensure_ascii=False, default=str)
    user = agent_runner._numbers(_user_text(case))
    return sorted(value for value in agent_runner._numbers(answer) if value not in user and value not in evidence)


def evaluate(case, client):
    expect = case["expect"]
    payload = {key: case[key] for key in ("event_id", "message", "history", "facility_id", "observation_at") if key in case}
    with (_failing_tool(case["fail_tool"]) if case.get("fail_tool") else nullcontext()):
        response = client.post("/api/agent/ask", json=payload)
    body = response.json()
    checks = {"http": response.status_code == expect.get("http", 200)}
    row = {"case_id": case["id"], "category": case["category"], "http_status": response.status_code}
    if response.status_code != 200:
        return {**row, "passed": all(checks.values()), "checks": checks, "status": None, "answer": None,
                "tool_inputs": [], "diagnostics": {}, "unsupported_numbers": [], "claim_hits": []}
    diagnostics = body.get("diagnostics") or {}
    calls = body.get("tool_calls", [])
    answer = body.get("answer", "")
    called = {}
    for call in calls:
        called.setdefault(call["tool_name"], []).append(
            {key: value for key, value in call["parameters"].items() if key not in _SCOPE_KEYS})
    checks["status"] = body.get("status") in expect["status"]
    if "context_mode" in expect:
        checks["context_mode"] = diagnostics.get("context_mode") == expect["context_mode"]
    if "completion_source" in expect:
        checks["completion_source"] = diagnostics.get("completion_source") == expect["completion_source"]
    if expect.get("no_tools"):
        checks["no_tools"] = not calls
    tool_ok = None
    if expect.get("tools") or expect.get("forbid_tools"):
        required = all(any(all(params.get(key) == value for key, value in wanted.items()) for params in called.get(name, []))
                       for name, wanted in expect.get("tools", {}).items())
        forbidden = not set(expect.get("forbid_tools", [])) & set(called)
        tool_ok = required and forbidden
        checks["tools"] = tool_ok
    for pattern in expect.get("must_say", []):
        checks[f"says:{pattern}"] = bool(re.search(pattern, answer))
    claim_hits = [pattern for pattern in expect.get("must_not_claim", []) if re.search(pattern, answer)]
    checks["no_forbidden_claim"] = not claim_hits
    # Server templates are fixed text; only model-written answers can invent numbers.
    unsupported = _unsupported_numbers(answer, calls, case) if diagnostics.get("completion_source") == "model" else []
    checks["numbers_grounded"] = not unsupported
    evidence = body.get("evidence_calls", [])
    return {**row, "passed": all(checks.values()), "checks": checks, "status": body.get("status"),
            "tool_ok": tool_ok, "evidence_valid": agent_runner._grounded_answer(answer, calls, evidence) if evidence else None,
            "unsupported_numbers": unsupported, "claim_hits": claim_hits, "answer": answer,
            "limitations": body.get("limitations", []),
            "tool_inputs": [{"tool_name": call["tool_name"], "parameters": call["parameters"]} for call in calls],
            "diagnostics": diagnostics}


def _percentile(values, share):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def _rate(rows, key):
    values = [row[key] for row in rows if row.get(key) is not None]
    return {"value": round(sum(values) / len(values), 3) if values else None, "n": len(values)}


def summarize(rows, skipped, mode):
    answered = [row for row in rows if row["http_status"] == 200]
    durations = [row["diagnostics"]["duration_ms"] for row in answered]
    tokens = [row["diagnostics"]["tokens"] for row in answered if row["diagnostics"].get("tokens")]
    successes = sum(row["passed"] for row in rows)
    total_tokens = sum(item["total"] for item in tokens)
    return {
        "mode": mode,
        "cases": len(rows),
        "skipped_needs_model": skipped,
        "passed": successes,
        "task_success_rate": round(successes / len(rows), 3) if rows else None,
        "tool_accuracy": _rate(rows, "tool_ok"),
        "evidence_validity": _rate(rows, "evidence_valid"),
        "unsupported_claim_rate": {
            "value": round(sum(bool(row["unsupported_numbers"] or row["claim_hits"]) for row in answered) / len(answered), 3) if answered else None,
            "n": len(answered)},
        "by_category": {category: {"passed": sum(row["passed"] for row in rows if row["category"] == category),
                                   "cases": sum(row["category"] == category for row in rows)} for category in CATEGORIES},
        "completion_sources": {source: sum(row["diagnostics"].get("completion_source") == source for row in answered)
                               for source in ("model", "registered_tools", "capability", "clarification", "unavailable")},
        "model_requests": {"total": sum(row["diagnostics"].get("model_requests", 0) for row in answered),
                           "per_case": round(sum(row["diagnostics"].get("model_requests", 0) for row in answered) / len(answered), 2) if answered else None},
        "tool_calls": {"total": sum(len(row["tool_inputs"]) for row in answered)},
        "tokens": {"total": total_tokens, "per_success": round(total_tokens / successes) if successes and tokens else None,
                   "cases_reporting": len(tokens)},
        "latency_ms": {"p50": _percentile(durations, 0.5), "p95": _percentile(durations, 0.95), "max": max(durations, default=None)},
        "failures": sorted({f"{failure['stage']}/{failure['code']}" for row in answered for failure in row["diagnostics"].get("failures", [])}),
        # Cases whose model path broke on transport (quota, network); their scores do not measure model quality.
        "model_transport_errors": [row["case_id"] for row in answered if any(
            failure["code"] in {"model_http_error", "model_connection_failed"} for failure in row["diagnostics"].get("failures", []))],
    }


def _versions():
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "backend/app", "backend/evaluation"], cwd=root,
                                    capture_output=True, text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    digest = lambda text: hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return {"git_commit": commit, "agent_code_uncommitted": dirty, "provider": agent_runner.agent_llm_provider(),
            "model": agent_runner.agent_model_id(),
            "system_prompt_sha256": digest(agent_runner._SYSTEM_PROMPT),
            "facility_prompt_sha256": digest(agent_runner._system_prompt({"selected_facility": True})),
            "cases_sha256": digest(CASES.read_text(encoding="utf-8"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    parser.add_argument("--case", action="append", default=[], help="case ID; repeat to select multiple")
    parser.add_argument("--category", action="append", default=[], choices=CATEGORIES)
    parser.add_argument("--output", type=Path, required=True, help="local JSON report, e.g. docs/local/agent-benchmark.json")
    parser.add_argument("--seconds-per-request", type=float, default=0.0,
                        help="live: pause this long per model request after each case (5 keeps under 12 requests/minute)")
    parser.add_argument("--provider", choices=("gemini", "ollama"), help="live: overrides AGENT_LLM_PROVIDER for this run")
    parser.add_argument("--model", help="live: Gemini or Ollama model name for this run")
    # Measurement switches for A/B runs on one code version; the product has no such flags.
    parser.add_argument("--no-trim", action="store_true", help="send full tool results to the model (before week-3 O1)")
    parser.add_argument("--full-catalogue", action="store_true", help="send every catalogue field to the model (before week-3 O2)")
    args = parser.parse_args()
    # Process-local settings so the report's version block names the provider that actually answered.
    if args.provider:
        os.environ["AGENT_LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["OLLAMA_MODEL" if agent_runner.agent_llm_provider() == "ollama" else "GEMINI_MODEL"] = args.model
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    unknown = set(args.case) - {case["id"] for case in cases}
    if unknown:
        parser.error(f"Unknown case IDs: {sorted(unknown)}")
    cases = [case for case in cases if (not args.case or case["id"] in args.case)
             and (not args.category or case["category"] in args.category)]
    skipped = [case["id"] for case in cases if args.mode == "offline" and case.get("needs_model")]
    cases = [case for case in cases if case["id"] not in skipped]
    if args.mode == "live" and not agent_runner.agent_model_status()["available"]:
        print(f"Live benchmark unavailable: {agent_runner.agent_model_status()['reason']}")
        return 2
    outage = patch("app.agent_runner._model_action", side_effect=LlmPlannerUnavailable("offline benchmark")) if args.mode == "offline" else nullcontext()
    # The benchmark is one local process; lift the public per-client limits for it in both modes.
    limits = patch.dict(os.environ, {"FLOODOPS_AGENT_PER_MINUTE": "1000", "FLOODOPS_AGENT_PER_DAY": "1000",
                                    "FLOODOPS_AGENT_GLOBAL_PER_DAY": "1000", "FLOODOPS_TWIN_MODE": "replay"})
    variant = patch.multiple(agent_runner, **{
        **({"_MODEL_HIDDEN_FIELDS": {}} if args.no_trim else {}),
        **({"_MODEL_CATALOGUE_FIELDS": ("name", "description", "input_fields", "output", "use_when", "parameters",
                                        "can_say", "cannot_say", "examples")} if args.full_catalogue else {}),
    }) if args.no_trim or args.full_catalogue else nullcontext()
    rows = []
    with limits, outage, variant, TestClient(app) as client:
        agent_limiter.reset()
        for case in cases:
            row = evaluate(case, client)
            rows.append(row)
            print(json.dumps({"case_id": row["case_id"], "passed": row["passed"], "status": row["status"],
                              "failed_checks": [key for key, ok in row["checks"].items() if not ok]}, ensure_ascii=False), flush=True)
            # Stay under the provider's per-minute quota; an HTTP 429 would score quota, not quality.
            time.sleep(args.seconds_per_request * row["diagnostics"].get("model_requests", 0))
    summary = summarize(rows, skipped, args.mode)
    versions = {**_versions(), "variant": {"trim_observations": not args.no_trim, "slim_catalogue": not args.full_catalogue}}
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "versions": versions, "summary": summary, "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary["passed"] == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

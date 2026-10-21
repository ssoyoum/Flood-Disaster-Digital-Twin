"""Aggregate opt-in Agent JSONL traces without printing prompts or tool payloads."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path


def summarize(lines):
    statuses, failures, tools = Counter(), Counter(), Counter()
    durations, seen = [], set()
    invalid = duplicates = requests = token_cases = tokens = 0
    for line in lines:
        try:
            row = json.loads(line)
            diag = row["diagnostics"]
            duration = diag["duration_ms"]
            request_id = diag["request_id"]
            if row["status"] not in {"ANSWERED", "NEEDS_DATA", "UNAVAILABLE"} or not isinstance(request_id, str) or not request_id:
                raise ValueError("invalid contract")
            if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
                raise ValueError("invalid duration")
            calls = row.get("tool_calls", [])
            failure_keys = [f"{f['stage']}/{f['code']}" for f in diag.get("failures", [])]
            tool_names = [c["tool_name"] for c in calls]
            model_requests = diag.get("model_requests", 0)
            usage = diag.get("tokens")
            total = usage["total"] if usage else 0
            if any(type(n) is not int or n < 0 for n in (model_requests, total)):
                raise ValueError("invalid counts")
        except (ValueError, TypeError, KeyError):
            invalid += 1
            continue
        if request_id in seen:
            duplicates += 1
            continue
        seen.add(request_id)
        statuses[row["status"]] += 1
        durations.append(duration)
        failures.update(failure_keys)
        tools.update(tool_names)
        requests += model_requests
        token_cases += bool(usage)
        tokens += total
    durations.sort()

    def percentile(p):
        return durations[max(0, math.ceil(len(durations) * p) - 1)] if durations else None

    return {
        "requests": len(durations), "invalid_lines": invalid, "duplicate_requests": duplicates,
        "statuses": dict(statuses), "failures": dict(failures), "tool_calls": dict(tools),
        "answered_rate": statuses["ANSWERED"] / len(durations) if durations else None,
        "latency_ms": {"p50": percentile(.5), "p95": percentile(.95), "max": max(durations, default=None)},
        "model_requests": requests, "tokens": {"reported_cases": token_cases, "total": tokens},
        "scope": "Agent responses only; HTTP rejection/process loss and semantic correctness are not measured",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.trace.resolve():
        parser.error("Choose a new output path; preserve the source trace and prior reports")
    with args.trace.open(encoding="utf-8") as handle:
        result = summarize(handle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["requests"] and not result["invalid_lines"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

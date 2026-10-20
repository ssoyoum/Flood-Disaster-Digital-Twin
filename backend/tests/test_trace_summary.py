import json
from backend.evaluation.summarize_traces import summarize


def record(request_id, duration, status="ANSWERED", **diag):
    return json.dumps({"status": status, "answer": "private text not included",
                       "tool_calls": [{"tool_name": "get_event", "result": {"secret": "not included"}}],
                       "diagnostics": {"request_id": request_id, "duration_ms": duration, **diag}})


def test_aggregates_failure_latency_and_reported_cost_without_payloads():
    result = summarize([record("a", 10), record("b", 100, "UNAVAILABLE", model_requests=1,
                        tokens={"total": 42}, failures=[{"stage": "request", "code": "request_timeout"}])])
    assert result["answered_rate"] == .5
    assert result["latency_ms"] == {"p50": 10, "p95": 100, "max": 100}
    assert result["failures"] == {"request/request_timeout": 1}
    assert result["tokens"] == {"reported_cases": 1, "total": 42}
    assert "private" not in json.dumps(result) and "secret" not in json.dumps(result)


def test_duplicates_and_invalid_or_nonfinite_timings_do_not_improve_rates():
    result = summarize([record("a", 10), record("a", 10), "broken", record("b", float("nan")), record("c", -1)])
    assert result["requests"] == 1
    assert result["duplicate_requests"] == 1
    assert result["invalid_lines"] == 3


def test_empty_trace_has_no_fake_success_or_latency():
    result = summarize([])
    assert result["answered_rate"] is None
    assert result["latency_ms"]["p95"] is None

"""Stage 5 profile in one fresh process: first vs second call per Agent tool, memory, and response size.

Run it alone; other CPU work on the machine inflates the timings. No model is called.
"""

import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("FLOODOPS_TWIN_MODE", "replay")
os.environ.update({"FLOODOPS_AGENT_PER_MINUTE": "1000", "FLOODOPS_AGENT_PER_DAY": "1000", "FLOODOPS_AGENT_GLOBAL_PER_DAY": "1000"})

FACILITY = {"facility_id": "gungpyeong2-underpass", "observation_at": "2023-07-15T08:00:00"}
PROBES = [
    ("osong-2023", "get_reconstruction", {}),
    ("osong-2023", "get_observation_summary", {}),
    ("osong-2023", "analyze_closure_timing", {"closure_times": ["08:20"]}),
    ("osong-2023", "get_exposure_inventory", {"radii_m": [500]}),
    ("osong-2023", "analyze_hand_threshold", {"reduction_m": 1.5}),
    ("seoul-2022", "get_reconstruction", {}),
    ("seoul-2022", "analyze_storage_capture", {"storage_m3": 400000}),
    ("pohang-2022", "get_reconstruction", {}),
    ("osong-2023", "get_facility_status", FACILITY),
    ("osong-2023", "get_facility_backtest", FACILITY),
    ("osong-2023", "get_criteria_review", FACILITY),
    ("osong-2023", "get_rise_forecast", FACILITY),
]
QUESTIONS = [
    {"event_id": "osong-2023", "message": "08:20에 통제했다면?"},
    {"event_id": "osong-2023", "message": "HAND 선택 임계를 1.5m 낮추면 단계별 붉은 셀이 어떻게 바뀌나요?"},
    {"event_id": "osong-2023", "message": "반경 500m 안 건물은 몇 동이야?"},
    {"event_id": "seoul-2022", "message": "도림천 빗물터널이 있었다면 얼마나 담았을까?"},
    {"event_id": "osong-2023", **FACILITY, "message": "기준별로 다른 해 권고가 몇 번 나오는지 비교해줘"},
]


def rss_mb():
    """Resident memory of this process (Windows working set or Linux VmRSS)."""
    if sys.platform == "win32":
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        counters = Counters(cb=ctypes.sizeof(Counters))
        kernel32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
        if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return round(counters.WorkingSetSize / 2**20, 1)
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return round(int(line.split()[1]) / 1024, 1)
    return None


def timed(fn):
    started = time.perf_counter()
    value = fn()
    return value, round((time.perf_counter() - started) * 1000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"rss_mb_start": rss_mb()}
    (agent_tools, schemas), import_ms = timed(lambda: (__import__("app.agent_tools", fromlist=["x"]), __import__("app.schemas", fromlist=["x"])))
    from app.main import app
    from app import agent_runner
    from fastapi.testclient import TestClient
    report.update({"import_ms": import_ms, "rss_mb_after_import": rss_mb(), "tools": []})
    for event_id, name, params in PROBES:
        request = schemas.AgentToolCallRequest(event_id=event_id, **params)
        result, first = timed(lambda: agent_tools.execute_agent_tool(name, event_id, request))
        _, second = timed(lambda: agent_tools.execute_agent_tool(name, event_id, request))
        report["tools"].append({"event_id": event_id, "tool": name, "first_ms": first, "second_ms": second,
                                "result_chars": len(json.dumps(result, ensure_ascii=False, default=str)), "rss_mb": rss_mb()})
    report["rss_mb_after_tools"] = rss_mb()
    report["responses"] = []
    with patch.object(agent_runner, "_model_action", side_effect=agent_runner.LlmPlannerUnavailable("profile")), TestClient(app) as client:
        for question in QUESTIONS:
            response, ms = timed(lambda: client.post("/api/agent/ask", json=question))
            body = response.json()
            report["responses"].append({"message": question["message"], "http": response.status_code, "api_ms": ms,
                                        "response_bytes": len(response.content), "tool_calls": [c["tool_name"] for c in body.get("tool_calls", [])],
                                        "largest_result_chars": max((len(json.dumps(c["result"], ensure_ascii=False, default=str))
                                                                     for c in body.get("tool_calls", [])), default=0)})
    report["rss_mb_end"] = rss_mb()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("tools", "responses")}, ensure_ascii=False))
    for row in report["tools"]:
        print(row["tool"], row["event_id"], row["first_ms"], row["second_ms"], row["result_chars"], row["rss_mb"])
    for row in report["responses"]:
        print(row["api_ms"], row["response_bytes"], row["tool_calls"])


if __name__ == "__main__":
    main()

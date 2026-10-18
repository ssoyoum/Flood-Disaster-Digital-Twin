"""Compare official flood forecast issuances with the observed water level and with the FloodOps review rule.

For every 홍수경보·홍수주의보 issuance (발령·변경발령) at a gauge with a stored hourly series, this finds:

- when the observed level actually crossed the level the forecast was about (경보 → warning, 주의보 → advisory),
- the peak level in the following 24 hours and whether the planned flood level was reached,
- when FloodOps' review rule (river_stage_v1: observed ≥ warning and, at the current rate, the planned flood
  level within 60 minutes, or already reached) would first have fired, on the hourly series.

It answers two questions the pitch depends on: does the official system already warn before the water gets
there (lead of the issuance over the observed crossing), and does the observation-based rule add anything on top
of it (rule time − issuance time).

    python data/scripts/compare_official_forecasts.py

Inputs: data/processed/flood_forecast/flood_forecast_issuances.csv (collect_flood_forecast_issuance.py),
data/processed/hrfco/waterlevel_{code}_1H.csv, data/manifests/hrfco-stations.json.
Outputs: data/processed/flood_forecast/official_vs_observed.csv and official_vs_observed_summary.json.

Thresholds change over time (e.g. 괴산 목도교 경보 4.5 m in 2020, 7.1 m in the 2026 catalogue), so each issuance is
judged against the threshold in force when it was issued: the level quoted in the issuance notes, else the
forecast level (59 of 64 issuances that quote both have the forecast equal to the threshold), else the current
catalogue value (issuances from 2024 carry no forecast level). `threshold_source` records which one was used.

Hourly data can miss a short peak and the rule's rate is the change over one hour, so rule times are a coarse
upper bound of what the 10-minute rule would do.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.national_watch import consistent_levels  # noqa: E402  (read-only reuse of the level sanity rule)

ISSUANCES = ROOT / "data" / "processed" / "flood_forecast" / "flood_forecast_issuances.csv"
SERIES = ROOT / "data" / "processed" / "hrfco"
CATALOG = ROOT / "data" / "manifests" / "hrfco-stations.json"
OUT = ROOT / "data" / "processed" / "flood_forecast"
LEVEL_KEYS = {"attention": "attwl", "advisory": "wrnwl", "warning": "almwl", "planned_flood": "pfh"}
WINDOW_BEFORE = timedelta(hours=12)
WINDOW_AFTER = timedelta(hours=24)
LEAD_THRESHOLD_MIN = 60


@lru_cache(maxsize=1)
def levels_by_station() -> dict[str, dict[str, float]]:
    raw = json.loads(CATALOG.read_text(encoding="utf-8"))["kinds"]["waterlevel"]
    rows = raw["stations"] if isinstance(raw, dict) else raw
    out = {}
    for row in rows:
        levels = {key: float(row[src]) for key, src in LEVEL_KEYS.items() if row.get(src) not in (None, "", 0, "0")}
        out[str(row["code"])] = consistent_levels(levels)
    return out


@lru_cache(maxsize=256)
def series(code: str) -> tuple[tuple[datetime, float], ...]:
    path = SERIES / f"waterlevel_{code}_1H.csv"
    if not path.exists():
        return ()
    out = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                out.append((datetime.strptime(row["timestamp_kst"], "%Y-%m-%d %H:%M"), float(row["wl"])))
            except (ValueError, TypeError):
                continue
    return tuple(out)


def minutes(a: datetime | None, b: datetime) -> int | None:
    return None if a is None else int((a - b).total_seconds() // 60)


def rule_fires(level: float, previous: float | None, levels: dict[str, float]) -> bool:
    warning, pfh = levels.get("warning"), levels.get("planned_flood")
    if warning is None or pfh is None or level < warning:
        return False
    if level >= pfh:
        return True
    if previous is None:
        return False
    rate_per_10min = (level - previous) / 6
    return rate_per_10min > 0 and (pfh - level) / rate_per_10min * 10 <= LEAD_THRESHOLD_MIN


NOTE_LEVELS = {"warning": re.compile(r"경보수위\s*:\s*[^-]*?수위표\s*기준\s*([0-9.]+)\s*m"),
               "advisory": re.compile(r"주의보수위\s*:\s*[^-]*?수위표\s*기준\s*([0-9.]+)\s*m"),
               "planned_flood": re.compile(r"계획홍수위\s*:\s*[^-]*?수위표\s*기준\s*([0-9.]+)\s*m")}


def levels_at_issue(issue: dict, current: dict[str, float]) -> tuple[dict[str, float], str]:
    """The thresholds in force at the issuance (see module docstring)."""
    levels = dict(current)
    source = "current"
    for key, pattern in NOTE_LEVELS.items():
        match = pattern.search(issue.get("notes", ""))
        if match:
            levels[key] = float(match.group(1))
            source = "notes"
    target_key = "warning" if "경보" in issue["kind"] else "advisory"
    if source != "notes" and issue.get("forecast_level_m") and "발령" in issue["kind"]:
        levels[target_key] = float(issue["forecast_level_m"])
        source = "forecast_level"
    return levels, source


def assess(issue: dict) -> dict | None:
    code = issue["station_code"]
    current = levels_by_station().get(code) or {}
    data = series(code)
    if not data or not issue["issued_at"]:
        return None
    levels, threshold_source = levels_at_issue(issue, current)
    issued = datetime.fromisoformat(issue["issued_at"])
    target_key = "warning" if "경보" in issue["kind"] else "advisory"
    target = levels.get(target_key)
    window = [(t, v) for t, v in data if issued - WINDOW_BEFORE <= t <= issued + WINDOW_AFTER]
    if not window:
        return None
    crossed = next((t for t, v in window if target is not None and v >= target), None)
    pfh_cross = next((t for t, v in window if levels.get("planned_flood") is not None and v >= levels["planned_flood"]), None)
    peak_time, peak = max(window, key=lambda item: item[1])
    rule = None
    for index, (t, v) in enumerate(window):
        previous = window[index - 1][1] if index else None
        if rule_fires(v, previous, levels):
            rule = t
            break
    return {
        "issued_at": issue["issued_at"], "kind": issue["kind"], "station_code": code, "station_name": issue["station_name"], "river": issue["river"],
        "target": target_key, "target_level_m": target, "threshold_source": threshold_source, "current_target_level_m": current.get(target_key),
        "level_at_issue_m": issue["level_at_issue_m"], "forecast_level_m": issue["forecast_level_m"],
        "forecast_time": issue["forecast_time"], "observed_cross_at": crossed.isoformat(timespec="minutes") if crossed else "",
        "issue_lead_over_crossing_min": minutes(crossed, issued), "peak_level_m": peak, "peak_at": peak_time.isoformat(timespec="minutes"),
        "planned_flood_m": levels.get("planned_flood"), "planned_flood_reached_at": pfh_cross.isoformat(timespec="minutes") if pfh_cross else "",
        "rule_fires_at": rule.isoformat(timespec="minutes") if rule else "", "rule_minus_issue_min": minutes(rule, issued),
    }


def describe(values: list[int]) -> dict:
    if not values:
        return {"n": 0}
    values = sorted(values)
    q = statistics.quantiles(values, n=4) if len(values) >= 4 else [values[0], statistics.median(values), values[-1]]
    return {"n": len(values), "median_min": statistics.median(values), "p25_min": q[0], "p75_min": q[-1]}


def main() -> None:
    with ISSUANCES.open(encoding="utf-8") as handle:
        issues = [row for row in csv.DictReader(handle) if "해제" not in row["kind"]]
    rows = [r for r in (assess(issue) for issue in issues) if r]
    with (OUT / "official_vs_observed.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    summary: dict = {"built_at": datetime.now().isoformat(timespec="seconds"), "issuances_compared": len(rows),
                     "window": "issue −12 h … +24 h, hourly series", "rule": "river_stage_v1 on hourly data (rate = 1-hour change)"}
    summary["threshold_source"] = {key: sum(1 for r in rows if r["threshold_source"] == key) for key in ("notes", "forecast_level", "current")}
    summary["threshold_changed_since_issue"] = sum(1 for r in rows if r["threshold_source"] != "current" and r["current_target_level_m"] is not None
                                                   and r["target_level_m"] is not None and abs(r["current_target_level_m"] - r["target_level_m"]) >= 0.05)
    for kind in ("경보", "주의보"):
        # 변경발령 also covers downgrades (경보 → 주의보 while falling); only issuances that raise the alert count here.
        group = [r for r in rows if kind in r["kind"] and not (kind == "주의보" and "변경" in r["kind"])]
        crossed = [r for r in group if r["issue_lead_over_crossing_min"] is not None]
        before = [r for r in crossed if r["issue_lead_over_crossing_min"] > 0]
        summary[kind] = {
            "issuances": len(group),
            "target_crossed": len(crossed),
            "target_never_crossed": len(group) - len(crossed),
            "issued_before_crossing": len(before),
            "issue_lead_over_crossing": describe([r["issue_lead_over_crossing_min"] for r in crossed]),
        }
        if kind == "경보":
            fired = [r for r in group if r["rule_minus_issue_min"] is not None]
            summary[kind].update({
                "planned_flood_reached": sum(1 for r in group if r["planned_flood_reached_at"]),
                "rule_fired": len(fired),
                "rule_before_issue": sum(1 for r in fired if r["rule_minus_issue_min"] < 0),
                "rule_minus_issue": describe([r["rule_minus_issue_min"] for r in fired]),
            })
    (OUT / "official_vs_observed_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

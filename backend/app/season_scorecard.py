"""Post-season scorecard: the facility rule's recommendations against the operator's own closure records.

The rule is replayed over the stored 10-minute water levels of one flood season (May 15 – Oct 15), which gives
review episodes. Each closure record is then matched to an episode:

- hit: the rule recommended a review and the facility was closed (lead = closure − first recommendation;
  negative means the operator closed before the rule spoke)
- not closed: the rule recommended, the operator recorded a decision not to close (an operator-judged false alarm)
- unrecorded: the rule recommended and nothing was recorded (unknown, not a false alarm)
- miss: the facility was closed without any recommendation nearby (the rule did not see it)

A closure matches an episode when it starts within MATCH_WINDOW before the episode or after its end.
The same matching is repeated for every criteria candidate so the operator can see which rule this season's
records support. Nothing here changes the registered rule.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median
from typing import Any

from . import closure_log, twin

MATCH_WINDOW = twin.EPISODE_GAP
SEASON_START = (5, 15)
SEASON_END = (10, 15)


def _season_series(facility_id: str, season: int) -> tuple[tuple[datetime, float], ...]:
    start = datetime(season, *SEASON_START)
    end = datetime(season, *SEASON_END, 23, 59)
    return tuple(row for row in twin._review_series(facility_id) if start <= row[0] <= end)


def available_seasons(facility_id: str) -> list[int]:
    return sorted({t.year for t, _ in twin._review_series(facility_id)})


def _episodes(series, levels: dict[str, float], stage_floor: str, lead_threshold_min: int, rate_window_min: int) -> list[dict[str, Any]]:
    flags = twin._review_flags(series, levels, stage_floor, lead_threshold_min, rate_window_min)
    return twin._review_episodes(series, flags, levels)


def match(episodes: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Pair closure records with review episodes; see the module docstring for the four outcomes."""

    rows: list[dict[str, Any]] = []
    used: set[str] = set()
    for episode in episodes:
        start, end = datetime.fromisoformat(episode["start"]), datetime.fromisoformat(episode["end"])
        near = [r for r in records if start - MATCH_WINDOW <= datetime.fromisoformat(r["started_at"]) <= end + MATCH_WINDOW]
        closed = sorted((r for r in near if r["kind"] == "CLOSED"), key=lambda r: r["started_at"])
        declined = [r for r in near if r["kind"] == "NOT_CLOSED"]
        if closed:
            first = closed[0]
            outcome, lead = "hit", int((datetime.fromisoformat(first["started_at"]) - start).total_seconds() // 60)
            linked = closed
        elif declined:
            outcome, lead, linked = "not_closed", None, declined
        else:
            outcome, lead, linked = "unrecorded", None, []
        used.update(r["record_id"] for r in linked)
        rows.append({"outcome": outcome, "episode": episode, "records": linked, "lead_min": lead})
    for record in records:
        if record["record_id"] in used:
            continue
        # A decision not to close with no recommendation around it agrees with the rule; it is shown, not scored.
        rows.append({"outcome": "miss" if record["kind"] == "CLOSED" else "quiet", "episode": None, "records": [record], "lead_min": None})
    rows.sort(key=lambda row: row["episode"]["start"] if row["episode"] else row["records"][0]["started_at"])
    leads = [row["lead_min"] for row in rows if row["outcome"] == "hit"]
    counts = {key: sum(1 for row in rows if row["outcome"] == key) for key in ("hit", "not_closed", "unrecorded", "miss", "quiet")}
    return {"rows": rows, "counts": counts, "median_lead_min": median(leads) if leads else None}


def compute(facility_id: str, season: int) -> dict[str, Any]:
    facility = twin.FACILITIES[facility_id]
    if not facility.get("history_series"):
        raise LookupError(f"No stored history for {facility_id}")
    seasons = available_seasons(facility_id)
    series = _season_series(facility_id, season)
    rule = facility["control_rule"]
    levels = facility["gauge"]["levels_m"]
    rate = rule.get("rate_window_min", 30)
    records = closure_log.list_records(facility_id, season)
    current = match(_episodes(series, levels, rule["stage_floor"], rule["lead_threshold_min"], rate), records) if series else match([], records)
    candidates = []
    for floor in twin.CRITERIA_FLOORS:
        for lead in twin.CRITERIA_LEADS:
            result = match(_episodes(series, levels, floor, lead, rate), records) if series else match([], records)
            candidates.append({"stage_floor": floor, "lead_threshold_min": lead,
                               "is_current_rule": floor == rule["stage_floor"] and lead == rule["lead_threshold_min"],
                               "episodes": sum(1 for row in result["rows"] if row["episode"]),
                               "counts": result["counts"], "median_lead_min": result["median_lead_min"]})
    return {
        "facility_id": facility_id,
        "facility": facility["name"],
        "season": season,
        "available_seasons": seasons,
        "window": {"start": datetime(season, *SEASON_START).isoformat(timespec="minutes"), "end": datetime(season, *SEASON_END, 23, 59).isoformat(timespec="minutes"),
                   "series_from": series[0][0].isoformat(timespec="minutes") if series else None,
                   "series_to": series[-1][0].isoformat(timespec="minutes") if series else None, "readings": len(series),
                   "max_water_level_m": max((wl for _, wl in series), default=None)},
        "rule": rule,
        "levels_m": levels,
        "records": len(records),
        **current,
        "candidates": candidates,
        "match_window_min": int(MATCH_WINDOW.total_seconds() // 60),
        "method": "규칙을 시즌(5/15–10/15) 저장 10분 수위에 재생해 권고 구간을 만들고, 담당자 통제 기록을 권고 구간 앞뒤 6시간 안에서 짝짓는다.",
        "limitations": [
            "통제 기록은 이 서버에 담당자가 남긴 것만 센다. 기록이 없는 권고는 오경보가 아니라 «기록 없음»이다.",
            "«막지 않음»은 담당자 판단이며 실제 침수 여부는 확인하지 않는다.",
            "저장된 수위가 끝나는 시각 이후의 권고는 아직 계산되지 않는다.",
        ],
    }

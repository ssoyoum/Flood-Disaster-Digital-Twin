"""Official flood forecasts (홍수주의보·홍수경보) as an input, live and for replay.

The national comparison (docs/PLATFORM_DATA.md §3-1) found the official warning comes about an hour before the
observed level gets there, and the observation-only review rule about 50 minutes after the warning. So the
official forecast is a leading input FloodOps should read, not a signal to beat. This module only provides it:

- `live_issuances()`: the last 24 hours from HRFCO `fldfct/list.json` (cached 5 minutes)
- `active_at(at)`: which gauges are under an issuance at a past time, from the collected history
  (data/processed/flood_forecast/flood_forecast_issuances.csv, collect_flood_forecast_issuance.py)
- `active_now()`: the same for the live feed

An issuance is active until a 해제 for the same gauge, or for at most ACTIVE_HOURS when the history has no
해제 (collection covers May–October).
"""

from __future__ import annotations

import csv
import json
import os
import threading
import urllib.request
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORY_FILE = REPO_ROOT / "data" / "processed" / "flood_forecast" / "flood_forecast_issuances.csv"
LIVE_URL = "https://api.hrfco.go.kr/{key}/fldfct/list.json"
REFRESH_SECONDS = 300
ACTIVE_HOURS = 72
LEVEL = {"홍수주의보": "advisory", "홍수경보": "warning"}
LEVEL_KO = {"advisory": "홍수주의보", "warning": "홍수경보"}

_LOCK = threading.Lock()
_LIVE: dict[str, Any] = {"fetched_at": None, "rows": [], "error": None}


def _stamp(value: str) -> str:
    value = (value or "").strip()
    try:
        return datetime.strptime(value, "%Y%m%d%H%M").isoformat(timespec="minutes")
    except ValueError:
        return value


def _number(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalise_live(row: dict[str, Any]) -> dict[str, Any]:
    return {"issued_at": _stamp(row.get("ancdt", "")), "kind": (row.get("kind") or "").strip(), "number": (row.get("no") or "").strip(),
            "office": (row.get("ancnm") or "").strip(), "station_code": (row.get("sttnm") or "").strip(), "station_name": (row.get("obsnm") or "").strip(),
            "river": (row.get("rvrnm") or "").strip(), "level_at_issue_m": _number(row.get("sttcurhgt")),
            "forecast_level_m": _number(row.get("sttfcthgt") or row.get("fcthgt")), "forecast_time": _stamp(row.get("sttfctdt") or row.get("fctdt") or ""),
            "trend": (row.get("sttcurcng") or "").strip()}


def level_of(kind: str) -> str | None:
    """'warning' or 'advisory' for 발령·변경발령, None for 해제."""
    if "해제" in kind:
        return None
    for word, level in LEVEL.items():
        if kind.startswith(word):
            return level
    return None


@lru_cache(maxsize=1)
def history() -> tuple[dict[str, Any], ...]:
    if not HISTORY_FILE.exists():
        return ()
    with HISTORY_FILE.open(encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            row = dict(row)
            row["level_at_issue_m"] = _number(row.get("level_at_issue_m"))
            row["forecast_level_m"] = _number(row.get("forecast_level_m"))
            rows.append(row)
    return tuple(sorted(rows, key=lambda r: r["issued_at"]))


def _active(rows: list[dict[str, Any]], at: datetime) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row["issued_at"] or datetime.fromisoformat(row["issued_at"]) > at:
            continue
        latest[row["station_code"]] = row  # rows are in time order, so the last one wins
    out = {}
    for code, row in latest.items():
        level = level_of(row["kind"])
        issued = datetime.fromisoformat(row["issued_at"])
        if level is None or at - issued > timedelta(hours=ACTIVE_HOURS):
            continue
        out[code] = {**{k: row.get(k) for k in ("issued_at", "kind", "number", "office", "station_name", "river",
                                                 "level_at_issue_m", "forecast_level_m", "forecast_time")},
                     "level": level, "level_ko": LEVEL_KO[level], "minutes_since_issue": int((at - issued).total_seconds() // 60)}
    return out


def active_at(at: str | datetime) -> dict[str, dict[str, Any]]:
    """Gauges under an official issuance at a past time, keyed by station code."""
    moment = datetime.fromisoformat(at) if isinstance(at, str) else at
    return _active(list(history()), moment)


def live_issuances(force: bool = False) -> dict[str, Any]:
    from .llm_planner import _load_env_file_once  # imported here: llm_planner imports the agent tool catalogue

    _load_env_file_once()
    key = os.environ.get("HRFCO_API_KEY", "")
    now = datetime.now().replace(microsecond=0)
    with _LOCK:
        fetched = _LIVE["fetched_at"]
        if not force and fetched and (now - fetched).total_seconds() < REFRESH_SECONDS:
            return dict(_LIVE)
        if not key:
            _LIVE.update(fetched_at=now, rows=[], error="HRFCO_API_KEY is not configured")
            return dict(_LIVE)
        try:
            with urllib.request.urlopen(LIVE_URL.format(key=key), timeout=15) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body.get("content") if isinstance(body, dict) else body
            rows = [_normalise_live(r) for r in content] if isinstance(content, list) else []  # code 990 = none in 24 h
            _LIVE.update(fetched_at=now, rows=sorted(rows, key=lambda r: r["issued_at"]), error=None)
        except Exception as exc:  # the key sits in the URL path; never surface it
            _LIVE.update(fetched_at=now, error=f"{type(exc).__name__} while reading the HRFCO flood forecast feed")
    return dict(_LIVE)


def active_now() -> dict[str, dict[str, Any]]:
    feed = live_issuances()
    return _active(feed["rows"], datetime.now())


def summary(at: str | None = None) -> dict[str, Any]:
    """Counts and the active issuances for the board: live when `at` is None, from history otherwise."""
    if at:
        active, mode, error, fetched = active_at(at), "replay", None, None
    else:
        feed = live_issuances()
        active, mode, error, fetched = _active(feed["rows"], datetime.now()), "live", feed["error"], feed["fetched_at"]
    rows = sorted(active.items(), key=lambda item: (item[1]["level"] != "warning", item[1]["issued_at"]))
    return {"mode": mode, "at": at or datetime.now().isoformat(timespec="minutes"), "fetched_at": fetched.isoformat() if fetched else None,
            "error": error, "counts": {"warning": sum(1 for _, a in rows if a["level"] == "warning"), "advisory": sum(1 for _, a in rows if a["level"] == "advisory")},
            "active": [{"station_code": code, **item} for code, item in rows],
            "source": "HRFCO OpenAPI fldfct (홍수예보 발령)",
            "limitations": ["공식 특보는 관측소 단위이며 시설 단위 판단이 아니다.",
                            "재생 이력은 5~10월 수집분이다. 해제가 없으면 발령 후 72시간까지만 유효로 본다."]}

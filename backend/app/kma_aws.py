"""KMA AWS minute data (API hub `nph-aws2_min`) for the live pluvial rule.

Pluvial underpasses flood from the rain that falls on them, and HRFCO rain gauges are sparse in cities. KMA AWS
(736 stations on 2026-10-19, 1-minute updates) carries RN-15m, RN-60m, RN-12H and RN-DAY. The 활용신청 was approved
on 2026-10-19; `facility_risk` adds these stations to the live rain gauges (`kma:{stn}` codes).

The response is KMA's typ01 text: `#` comment lines, one of which names the columns, then whitespace-separated
rows. The column order is read from that header rather than assumed, so a different order or extra columns do not
break parsing; `parse()` raises if no header names YYMMDDHHMI and STN. Confirm the header on the first approved call
(`python data/scripts/probe_kma_aws.py`, which never prints the key).
"""

from __future__ import annotations

import json
import os
import re
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

LAG_MINUTES = 2
URL = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-aws2_min?tm2={tm}&stn=0&disp=0&help=1&authKey={key}"
RAIN_COLUMNS = {"RN-15m": "rain_15m_mm", "RN-60m": "rain_1h_mm", "RN-12H": "rain_12h_mm", "RN-DAY": "rain_day_mm"}
MISSING = {"-99", "-99.0", "-99.9", "-999", "-999.0"}


def _header(lines: list[str]) -> list[str] | None:
    for line in lines:
        if not line.startswith("#"):
            continue
        tokens = line.lstrip("#").split()
        if "YYMMDDHHMI" in tokens and "STN" in tokens:
            return tokens
    return None


def _value(text: str) -> float | None:
    if text in MISSING:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return None if value < 0 else value


def parse(body: str) -> dict[str, dict[str, Any]]:
    """Rows keyed by AWS station number, with the rain columns renamed and missing values as None."""
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    columns = _header(lines)
    if columns is None:
        raise ValueError("no YYMMDDHHMI/STN header in the AWS response")
    out: dict[str, dict[str, Any]] = {}
    for line in lines:
        if line.startswith("#"):
            continue
        cells = line.replace(",", " ").split()
        if len(cells) < len(columns):
            continue
        row = dict(zip(columns, cells))
        try:
            time = datetime.strptime(row["YYMMDDHHMI"], "%Y%m%d%H%M")
        except ValueError:
            continue
        item: dict[str, Any] = {"stn": row["STN"], "time": time.isoformat(timespec="minutes")}
        for source, key in RAIN_COLUMNS.items():
            if source in row:
                item[key] = _value(row[source])
        out[row["STN"]] = item
    return out


def fetch(at: datetime | None = None, timeout: float = 15.0) -> dict[str, Any]:
    """Latest minute rows for all stations. Errors are reported without the key (it sits in the query string)."""
    from .llm_planner import _load_env_file_once  # imported here: llm_planner imports the agent tool catalogue

    _load_env_file_once()
    key = os.environ.get("KMA_API_HUB_KEY", "")
    if not key:
        return {"available": False, "error": "KMA_API_HUB_KEY is not configured", "rows": {}}
    # The current minute is still filling in (2026-10-19: 680/736 stations at 0 min, 696 from 1–2 min back).
    moment = (at or datetime.now() - timedelta(minutes=LAG_MINUTES)).strftime("%Y%m%d%H%M")
    try:
        with urllib.request.urlopen(URL.format(tm=moment, key=key), timeout=timeout) as response:
            body = response.read().decode("euc-kr", errors="replace")
    except urllib.error.HTTPError as exc:
        hint = " (API 허브에서 이 API의 활용신청 승인이 필요)" if exc.code in (401, 403) else ""
        return {"available": False, "error": f"HTTP {exc.code} from the KMA AWS minute API{hint}", "rows": {}}
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__} while reading the KMA AWS minute API", "rows": {}}
    try:
        rows = parse(body)
    except ValueError as exc:
        return {"available": False, "error": str(exc), "rows": {}}
    return {"available": bool(rows), "error": None, "requested_at": moment, "rows": rows}


# ---- station positions and rain totals for the facility rule -------------------------------------------
STATIONS_URL = "https://apihub.kma.go.kr/api/typ01/url/stn_inf.php?inf=AWS&stn=&tm={tm}&help=0&authKey={key}"
STATIONS_FILE = Path(__file__).resolve().parents[2] / "data" / "processed" / "kma" / "aws_stations.json"
REFRESH_SECONDS = 300
_LAW_ID = re.compile(r"^\d{10}$")
_LOCK = threading.Lock()
_TOTALS: dict[str, Any] = {"fetched_at": None, "observed_at": None, "rows": {}, "error": None}


def parse_stations(body: str) -> dict[str, dict[str, Any]]:
    """`stn_inf.php?inf=AWS` rows: STN LON LAT STN_SP HT HT_WD LAU STN_AD STN_KO STN_EN FCT_ID LAW_ID BASIN LAW_ADDR."""
    out: dict[str, dict[str, Any]] = {}
    for line in body.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split()
        law = next((i for i, cell in enumerate(cells) if _LAW_ID.match(cell)), None)
        if law is None or len(cells) < 12:
            continue
        try:
            lon, lat = float(cells[1]), float(cells[2])
        except ValueError:
            continue
        name = " ".join(cells[8:law - 2]) or cells[8]  # STN_KO, then STN_EN and FCT_ID before LAW_ID
        out[cells[0]] = {"stn": cells[0], "name": name, "lon": lon, "lat": lat, "address": " ".join(cells[law + 2:])}
    return out


def _key() -> str:
    from .llm_planner import _load_env_file_once

    _load_env_file_once()
    return os.environ.get("KMA_API_HUB_KEY", "")


@lru_cache(maxsize=1)
def stations() -> dict[str, dict[str, Any]]:
    """AWS station positions: the stored file, refreshed from the API when the file is missing."""
    if STATIONS_FILE.exists():
        return json.loads(STATIONS_FILE.read_text(encoding="utf-8"))["stations"]
    key = _key()
    if not key:
        return {}
    try:
        with urllib.request.urlopen(STATIONS_URL.format(tm=datetime.now().strftime("%Y%m%d%H%M"), key=key), timeout=20) as response:
            rows = parse_stations(response.read().decode("euc-kr", errors="replace"))
    except Exception:
        return {}
    if rows:
        STATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATIONS_FILE.write_text(json.dumps({"source": "KMA API hub stn_inf.php?inf=AWS", "fetched_at": datetime.now().isoformat(timespec="minutes"),
                                             "stations": rows}, ensure_ascii=False, indent=0), encoding="utf-8")
    return rows


def rain_totals(force: bool = False) -> dict[str, Any]:
    """Per-station 1·3·12-hour rain, keyed `kma:{stn}`, cached REFRESH_SECONDS.

    1 h = RN-60m and 12 h = RN-12H of the latest minute; 3 h = the RN-60m of the latest minute and of 60 and
    120 minutes before (three calls), only when all three are present.
    """
    now = datetime.now().replace(second=0, microsecond=0)
    with _LOCK:
        fetched = _TOTALS["fetched_at"]
        if not force and fetched and (now - fetched).total_seconds() < REFRESH_SECONDS:
            return dict(_TOTALS)
        latest = now - timedelta(minutes=LAG_MINUTES)
        frames = [fetch(latest - timedelta(minutes=60 * back)) for back in range(3)]
        if not frames[0]["available"]:
            _TOTALS.update(fetched_at=now, observed_at=None, rows={}, error=frames[0]["error"])
            return dict(_TOTALS)
        rows: dict[str, dict[str, Any]] = {}
        for stn, row in frames[0]["rows"].items():
            hours = [frame["rows"].get(stn, {}).get("rain_1h_mm") for frame in frames]
            rows[f"kma:{stn}"] = {"rain_10m_mm": None, "rain_15m_mm": row.get("rain_15m_mm"), "rain_1h_mm": row.get("rain_1h_mm"),
                                  "rain_3h_mm": round(sum(hours), 1) if all(h is not None for h in hours) else None,
                                  "rain_12h_mm": row.get("rain_12h_mm")}
        _TOTALS.update(fetched_at=now, observed_at=latest, rows=rows, error=None)
    return dict(_TOTALS)

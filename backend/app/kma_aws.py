"""KMA AWS minute data (API hub `nph-aws2_min`), ready for when the 활용신청 is approved.

Pluvial underpasses flood from the rain that falls on them, and HRFCO rain gauges are sparse in cities. KMA AWS
(about 500 stations, 1-minute updates) carries RN-15m, RN-60m, RN-12H and RN-DAY. Today the key returns 403 for
this API (TODO.md: 기상청 API 허브 활용신청), so nothing calls this module yet.

The response is KMA's typ01 text: `#` comment lines, one of which names the columns, then whitespace-separated
rows. The column order is read from that header rather than assumed, so a different order or extra columns do not
break parsing; `parse()` raises if no header names YYMMDDHHMI and STN. Confirm the header on the first approved call
(`python data/scripts/probe_kma_aws.py`, which never prints the key).
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

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
    moment = (at or datetime.now()).strftime("%Y%m%d%H%M")
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

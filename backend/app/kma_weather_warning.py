"""Current KMA heavy-rain alerts for the live facility risk floor.

The API Hub ``wrn_now_data.php`` reports current alerts by weather-warning zone.
Its zone labels are joined to a facility's municipality only when one name
contains the other; province-wide alerts match every facility in that province.
Unknown composite zones stay unmatched so a broad regional warning is not
mistakenly assigned to individual municipalities.
"""

from __future__ import annotations

import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from . import national_watch as nw

URL = "https://apihub.kma.go.kr/api/typ01/url/wrn_now_data.php"
REFRESH_SECONDS = 300
LEVEL_KO = {"advisory": "호우주의보", "warning": "호우경보"}

_LOCK = threading.Lock()
_FEED: dict[str, Any] = {"fetched_at": None, "available": False, "active": [], "error": None}


def _stamp(value: str) -> str | None:
    value = (value or "").strip()
    try:
        return datetime.strptime(value, "%Y%m%d%H%M").isoformat(timespec="minutes")
    except ValueError:
        return None


def _level(value: str) -> str | None:
    # The live response uses 주의/경보 (예비 = preliminary, not in effect); older docs show 1/2 or 주의보.
    value = (value or "").strip()
    if value == "1" or value.startswith("주의"):
        return "advisory"
    if value == "2" or "경보" in value:
        return "warning"
    return None


def parse(body: str) -> list[dict[str, Any]]:
    """Parse the KMA typ01 header and return active heavy-rain alert rows."""
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    required = {"REG_UP_KO", "REG_KO", "REG_ID", "TM_FC", "TM_EF", "WRN", "LVL", "CMD"}
    columns: list[str] | None = None
    for line in lines:
        if not line.startswith("#"):
            continue
        # Column names are padded with dashes to the field width ("REG_KO-----").
        tokens = [token.rstrip("-") for token in line.lstrip("#").split()]
        if required.issubset(tokens):
            columns = tokens
            break
    if columns is None:
        raise ValueError("no KMA warning header with REG_KO, WRN and LVL")

    out: list[dict[str, Any]] = []
    for line in lines:
        if line.startswith("#"):
            continue
        # Rows are comma-separated and end with "=", and ED_TM values contain spaces.
        cells = [cell.strip() for cell in line.rstrip("=").split(",")] if "," in line else line.split()
        if len(cells) < len(columns):
            continue
        row = dict(zip(columns, cells))
        kind = (row.get("WRN") or "").strip()
        if kind not in {"R", "호우"}:
            continue
        level = _level(row.get("LVL", ""))
        if level is None:
            continue
        command = (row.get("CMD") or "").strip()
        if any(word in command for word in ("해제", "취소", "종료")):
            continue
        area = (row.get("REG_KO") or "").strip()
        if not area:
            continue
        out.append({
            "region_code": (row.get("REG_ID") or "").strip(),
            "province": (row.get("REG_UP_KO") or "").strip(),
            "area": area,
            "level": level,
            "level_ko": LEVEL_KO[level],
            "issued_at": _stamp(row.get("TM_FC", "")),
            "effective_at": _stamp(row.get("TM_EF", "")),
            "command": command,
        })
    return out


def _request(key: str, tm: str = "") -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"fe": "f", "tm": tm, "disp": "0", "help": "1", "authKey": key})
    with urllib.request.urlopen(urllib.request.Request(f"{URL}?{query}"), timeout=15) as response:
        return parse(response.read().decode("euc-kr", errors="replace"))


def at(moment: datetime) -> dict[str, Any]:
    """Heavy-rain alert rows as of a past KST minute (`tm` on wrn_now_data.php). Uncached.

    The response holds only the latest command per zone, so an alert announced for a later minute replaces the one
    still in effect. Such rows are kept with `in_effect: False` instead of being read as "no alert".
    """
    from .llm_planner import _load_env_file_once

    _load_env_file_once()
    key = os.environ.get("KMA_API_HUB_KEY", "")
    if not key:
        return {"available": False, "rows": [], "error": "KMA_API_HUB_KEY is not configured"}
    try:
        rows = _request(key, moment.strftime("%Y%m%d%H%M"))
    except urllib.error.HTTPError as exc:
        return {"available": False, "rows": [], "error": f"HTTP {exc.code} from the KMA warning API"}
    except Exception as exc:
        return {"available": False, "rows": [], "error": f"{type(exc).__name__} while reading the KMA warning API"}
    for row in rows:
        row["in_effect"] = bool(row["effective_at"]) and datetime.fromisoformat(row["effective_at"]) <= moment
    return {"available": True, "rows": rows, "error": None}


def current(force: bool = False) -> dict[str, Any]:
    """Return the cached current warning feed; never include the API key in an error."""
    from .llm_planner import _load_env_file_once

    _load_env_file_once()
    now = datetime.now().replace(microsecond=0)
    with _LOCK:
        fetched = _FEED["fetched_at"]
        if not force and fetched and (now - fetched).total_seconds() < REFRESH_SECONDS:
            return dict(_FEED)
        key = os.environ.get("KMA_API_HUB_KEY", "")
        if not key:
            _FEED.update(fetched_at=now, available=False, active=[], error="KMA_API_HUB_KEY is not configured")
            return dict(_FEED)
        try:
            rows = _request(key)
            active = []
            for row in rows:
                effective = datetime.fromisoformat(row["effective_at"]) if row["effective_at"] else None
                if effective is None or effective <= now:
                    active.append(row)
            _FEED.update(fetched_at=now, available=True, active=active, error=None)
        except urllib.error.HTTPError as exc:
            hint = " (API Hub 활용신청 승인이 필요)" if exc.code in (401, 403) else ""
            _FEED.update(fetched_at=now, available=False, active=[], error=f"HTTP {exc.code} from the KMA warning API{hint}")
        except Exception as exc:
            _FEED.update(fetched_at=now, available=False, active=[], error=f"{type(exc).__name__} while reading the KMA warning API")
        return dict(_FEED)


def _compact(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isalnum())


def matches_facility(alert: dict[str, Any], facility: dict[str, Any]) -> bool:
    """Match a warning zone to a municipality conservatively, with province-wide fallback."""
    region = facility.get("region") or ""
    alert_region = nw.match_region(alert.get("province", "")) or nw.match_region(alert.get("area", ""))
    if alert_region and alert_region != region:
        return False

    area = alert.get("area", "")
    compact_area = _compact(area)
    aliases = nw._REGION_ALIASES.get(region, (region,))
    compact_aliases = {_compact(alias) for alias in aliases if alias}
    if compact_area in compact_aliases:
        return True

    sgg = facility.get("sgg")
    if not sgg:
        return False
    compact_sgg = _compact(sgg)
    # Strip province names from both labels; exact city/district names then match,
    # while an alert for a city also covers its facility sub-districts.
    for alias in compact_aliases:
        compact_area = compact_area.replace(alias, "")
        compact_sgg = compact_sgg.replace(alias, "")
    return bool(compact_area and compact_sgg and (compact_area in compact_sgg or compact_sgg in compact_area))


def for_facility(alerts: list[dict[str, Any]], facility: dict[str, Any], at: str | None = None) -> dict[str, Any] | None:
    moment = datetime.fromisoformat(at) if at else datetime.now()
    matches = []
    for alert in alerts:
        effective = datetime.fromisoformat(alert["effective_at"]) if alert.get("effective_at") else None
        if effective and effective > moment:
            continue
        if matches_facility(alert, facility):
            matches.append(alert)
    if not matches:
        return None
    matches.sort(key=lambda row: (row["level"] == "warning", row.get("issued_at") or ""), reverse=True)
    return matches[0]

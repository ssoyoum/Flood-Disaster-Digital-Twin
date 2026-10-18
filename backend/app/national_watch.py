"""National river-gauge watch.

Every HRFCO water-level station is classified against its *own* official levels (관심·주의보·경보·계획홍수위
from the station catalogue), with the current rate of rise and the minutes left to the planned flood level.
Facilities linked to a gauge (underpasses within 5 km on the same catalogue) ride along as the "watch" tier:
the link only says a gauge is nearby, not that it represents the facility's inflow. Only facilities in the
operational registry (data/facilities/registry.json) carry their own verified rule.

Sources:
- live: one bulk call per kind returns the latest value of every station (waterlevel/list/10M.json).
- replay: the stored hourly series under data/processed/hrfco for a chosen time (E2E and demos).
"""

from __future__ import annotations

import csv
import json
import math
import mmap
import os
import re
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = REPO_ROOT / "data" / "manifests" / "hrfco-stations.json"
LINKS_FILE = REPO_ROOT / "data" / "processed" / "facilities" / "facility_gauge_links.csv"
RIVERSIDE_FILE = REPO_ROOT / "data" / "processed" / "facilities" / "riverside_access.csv"
FACILITY_LINK_KM = 5.0
KIND_KO = {"underpass": "지하차도", "riverside_parking": "둔치·하천변 주차장", "riverside_park": "하천 둔치 공원", "riverbed_road": "하상도로"}
GROUP_KO = {"underpass": "지하차도", "riverside": "하천변 출입구"}
HOURLY_DIR = REPO_ROOT / "data" / "processed" / "hrfco"
LIVE_RAIN_HISTORY_FILE = REPO_ROOT / "data" / "interim" / "hrfco_live_rainfall_1h.json"
BULK_ENDPOINT = "https://api.hrfco.go.kr/{key}/{kind}/list/{interval}.json"
DEFAULT_REPLAY_AT = "2023-07-15T08:00:00"

STAGE_ORDER = ["unrated", "normal", "attention", "advisory", "warning", "planned_flood"]
STAGE_KO = {"unrated": "기준 없음", "normal": "정상", "attention": "관심", "advisory": "주의보", "warning": "경보", "planned_flood": "계획홍수위"}
LEVEL_KEYS = {"attention": "attwl", "advisory": "wrnwl", "warning": "almwl", "severe": "srswl", "planned_flood": "pfh"}
# Rise classes are display bins over the 10-minute rate; they are not an official grading.
RISE_CLASSES = [(0.30, "rapid", "급격"), (0.10, "fast", "빠름"), (0.02, "slow", "느림")]
STEP_SUSPECT_M = 3.0  # same jump rule as data/scripts/audit_hrfco_quality.py
REFRESH_SECONDS = 300
FRESH_MINUTES = {"10M": 30, "1H": 90}
# 기상청 강수강도 구분(시간당 mm): 약한 비 3 미만, 보통 비 3~15, 강한 비 15~30, 매우 강한 비 30 이상.
RAIN_CLASSES = [(30.0, "very_heavy", "매우 강한 비"), (15.0, "heavy", "강한 비"), (3.0, "moderate", "보통 비")]
RAIN_LINK_KM = 10.0  # a water-level gauge borrows the nearest rain gauge within this distance
RAIN_LIMITATIONS = [
    "실시간 강도는 최근 10분 강우를 6배 한 시간당 환산값이고, 재생은 저장된 1시간 강우다.",
    "하천 관측소 옆 강우는 10 km 안 가장 가까운 강우 관측소 값이며 유역 평균 강우가 아니다.",
    "비가 하천 수위에 반영되기까지 시간차가 있어 강우만으로 단계·침수를 판정하지 않는다.",
]

_REGION_ALIASES: dict[str, tuple[str, ...]] = {
    "서울": ("서울특별시", "서울시", "서울"),
    "부산": ("부산광역시", "부산시", "부산"),
    "대구": ("대구광역시", "대구시", "대구"),
    "인천": ("인천광역시", "인천시", "인천"),
    "광주": ("광주광역시", "광주시", "광주"),
    "대전": ("대전광역시", "대전시", "대전"),
    "울산": ("울산광역시", "울산시", "울산"),
    "세종": ("세종특별자치시", "세종시", "세종"),
    "경기": ("경기도", "경기"),
    "강원": ("강원특별자치도", "강원도", "강원"),
    "충북": ("충청북도", "충북"),
    "충남": ("충청남도", "충남"),
    "전북": ("전북특별자치도", "전라북도", "전북"),
    "전남": ("전남광주통합특별시", "전라남도", "전남"),
    "경북": ("경상북도", "겅상북도", "경북"),
    "경남": ("경상남도", "경남"),
    "제주": ("제주특별자치도", "제주도", "제주"),
}


def consistent_levels(levels: dict[str, float]) -> dict[str, float]:
    """Keep a station's levels only when they rise in stage order.

    Some catalogue rows (e.g. reservoir gauges reporting EL. m) list a planned flood level below the
    warning level; classifying against them would put a calm reservoir at the top stage. Such a station
    is left unrated rather than guessed at.
    """
    levels = dict(levels)
    lower = [levels[key] for key in ("attention", "advisory", "warning") if key in levels]
    # A planned flood level below the warning stages is the usual catalogue fault: drop it, keep the stages.
    if "planned_flood" in levels and lower and levels["planned_flood"] < max(lower):
        levels.pop("planned_flood")
    if "severe" in levels and lower and levels["severe"] < max(lower):
        levels.pop("severe")
    ordered = [levels[key] for key in ("attention", "advisory", "warning", "planned_flood") if key in levels]
    if any(later < earlier for earlier, later in zip(ordered, ordered[1:])):
        return {}
    return levels


def region_of(address: str) -> str:
    head = (address or "").split(" ")[0]
    for short, aliases in _REGION_ALIASES.items():
        if head in aliases:
            return short
    return "기타"


def match_region(text: str) -> str | None:
    """The region the user named, longest alias first so 전북 does not match inside 전북특별자치도 twice."""
    best: tuple[int, str] | None = None
    for short, aliases in _REGION_ALIASES.items():
        for alias in aliases:
            if alias in text and (best is None or len(alias) > best[0]):
                best = (len(alias), short)
    return best[1] if best else None


@dataclass(frozen=True)
class Station:
    code: str
    name: str
    agency: str
    address: str
    region: str
    lon: float
    lat: float
    datum_el_m: float | None
    levels_m: dict[str, float]
    flood_forecast: bool

    @property
    def short_name(self) -> str:
        inner = re.search(r"\(([^)]+)\)", self.name)
        return inner.group(1) if inner else self.name


@lru_cache(maxsize=1)
def stations() -> dict[str, Station]:
    raw = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))["kinds"]["waterlevel"]
    rows = raw["stations"] if isinstance(raw, dict) else raw
    out: dict[str, Station] = {}
    for row in rows:
        if row.get("lon") in (None, "") or row.get("lat") in (None, ""):
            continue  # a handful of catalogue rows carry no coordinates; they cannot sit on the map
        levels = consistent_levels({key: float(row[src]) for key, src in LEVEL_KEYS.items() if row.get(src) not in (None, "", 0)})
        out[str(row["code"])] = Station(
            code=str(row["code"]), name=row["name"], agency=row.get("agency", ""), address=row.get("address", ""),
            region=region_of(row.get("address", "")), lon=float(row["lon"]), lat=float(row["lat"]),
            datum_el_m=float(row["gdt"]) if row.get("gdt") not in (None, "") else None,
            levels_m=levels, flood_forecast=row.get("flood_forecast_station") == "Y",
        )
    return out


def _nearest_station(lon: float, lat: float, max_km: float) -> tuple[Station, float] | None:
    best: tuple[float, Station] | None = None
    for station in stations().values():
        if abs(station.lat - lat) > 0.06 or abs(station.lon - lon) > 0.08:
            continue
        distance = _km(lon, lat, station.lon, station.lat)
        if distance <= max_km and (best is None or distance < best[0]):
            best = (distance, station)
    return (best[1], round(best[0], 2)) if best else None


@lru_cache(maxsize=1)
def facility_catalog() -> tuple[dict[str, Any], ...]:
    """Every river-contact facility with coordinates, whether or not a river gauge is near it.

    - operational: registry facilities with their own verified gauge and rule (data/facilities/registry.json)
    - watch: the nearest water-level gauge is within FACILITY_LINK_KM; its stage stands in for the facility,
      which is a proximity link, not a verified inflow driver
    - rain_only: no gauge that close; the board shows the rain next to it and nothing about river stage
    """
    from .twin import FACILITIES
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for facility in FACILITIES.values():
        station = stations().get(facility["gauge"]["station_id"])
        out.append({"facility_id": facility["id"], "name": facility["name"], "kind": facility["kind"], "kind_ko": KIND_KO.get(facility["kind"], facility["kind"]),
                    "group": "underpass" if facility["kind"] == "underpass" else "riverside", "tier": "operational",
                    "region": station.region if station else "기타", "sgg": None, "lon": facility["location"][0], "lat": facility["location"][1],
                    "station_code": facility["gauge"]["station_id"], "distance_km": None, "river_name": None,
                    "event_id": facility.get("event_id"), "source": "운영 등록(data/facilities/registry.json)"})
        seen.add(facility["id"])
    raw: list[dict[str, Any]] = []
    if LINKS_FILE.exists():
        with LINKS_FILE.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["kind"] == "waterlevel" and row["rank"] == "1" and row["facility_source"] != "twin_registry":
                    raw.append({"facility_id": row["facility_id"], "name": row["facility_name"], "kind": "underpass", "sido": row.get("sido", ""),
                                "sgg": row.get("sgg") or None, "lon": float(row["facility_lon"]), "lat": float(row["facility_lat"]),
                                "river_name": None, "source": "국토교통부 지하차도 현황 + OSM 좌표"})
    if RIVERSIDE_FILE.exists():
        with RIVERSIDE_FILE.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                raw.append({"facility_id": row["facility_id"], "name": row["name"], "kind": row["kind"], "sido": row["sido"], "sgg": None,
                            "lon": float(row["lon"]), "lat": float(row["lat"]), "river_name": row["river_name"] or None,
                            "source": "OpenStreetMap 이름 + WAMIS 하천 선형 거리"})
    placed: dict[str, list[tuple[float, float]]] = {}
    for row in raw:
        if row["facility_id"] in seen:
            continue
        seen.add(row["facility_id"])
        # "하상도로", "천변공원" and the like say nothing on their own; the river name tells them apart.
        if row["river_name"] and len(row["name"]) <= 5 and row["river_name"] not in row["name"]:
            row["name"] = f"{row['river_name']} {row['name']}"
        if any(_km(row["lon"], row["lat"], lon, lat) < 2.0 for lon, lat in placed.get(row["name"], [])):
            continue  # two OSM segments of one road or park
        placed.setdefault(row["name"], []).append((row["lon"], row["lat"]))
        near = _nearest_station(row["lon"], row["lat"], FACILITY_LINK_KM)
        region = region_of(row["sido"]) if row["sido"] else "기타"
        if region == "기타" and near:
            region = near[0].region
        out.append({"facility_id": row["facility_id"], "name": row["name"], "kind": row["kind"], "kind_ko": KIND_KO.get(row["kind"], row["kind"]),
                    "group": "underpass" if row["kind"] == "underpass" else "riverside", "tier": "watch" if near else "rain_only",
                    "region": region, "sgg": row["sgg"], "lon": row["lon"], "lat": row["lat"],
                    "station_code": near[0].code if near else None, "distance_km": near[1] if near else None,
                    "river_name": row["river_name"], "event_id": None, "source": row["source"]})
    return tuple(out)


@lru_cache(maxsize=1)
def facility_links() -> dict[str, list[dict[str, Any]]]:
    """Facilities keyed by the gauge that stands in for them (operational and watch tiers only)."""
    keys = ("facility_id", "name", "kind", "kind_ko", "group", "tier", "region", "sgg", "lon", "lat", "distance_km", "event_id")
    by_station: dict[str, list[dict[str, Any]]] = {}
    for facility in facility_catalog():
        if facility["station_code"]:
            by_station.setdefault(facility["station_code"], []).append({key: facility[key] for key in keys})
    return by_station


def facility_index() -> dict[str, dict[str, Any]]:
    return {facility["facility_id"]: dict(facility) for facility in facility_catalog()}


@dataclass(frozen=True)
class RainGauge:
    code: str
    name: str
    region: str
    lon: float
    lat: float

    @property
    def short_name(self) -> str:
        inner = re.search(r"\(([^)]+)\)", self.name)
        return inner.group(1) if inner else self.name


@lru_cache(maxsize=1)
def rain_gauges() -> dict[str, RainGauge]:
    raw = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))["kinds"]["rainfall"]
    rows = raw["stations"] if isinstance(raw, dict) else raw
    return {str(row["code"]): RainGauge(str(row["code"]), row["name"], region_of(row.get("address", "")), float(row["lon"]), float(row["lat"]))
            for row in rows if row.get("lon") not in (None, "") and row.get("lat") not in (None, "")}


def _km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    # Equirectangular is within a few metres of haversine at 10 km in Korea.
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6371.0 * math.hypot(x, y)


@lru_cache(maxsize=1)
def rain_neighbours() -> dict[str, tuple[tuple[str, float], ...]]:
    """Rain gauges within RAIN_LINK_KM of each water-level gauge, nearest first."""
    gauges = list(rain_gauges().values())
    out: dict[str, tuple[tuple[str, float], ...]] = {}
    for station in stations().values():
        near = sorted((_km(station.lon, station.lat, gauge.lon, gauge.lat), gauge.code) for gauge in gauges
                      if abs(gauge.lat - station.lat) < 0.1 and abs(gauge.lon - station.lon) < 0.13)
        out[station.code] = tuple((code, round(distance, 1)) for distance, code in near if distance <= RAIN_LINK_KM)
    return out


def rain_class(mm_per_hour: float | None) -> tuple[str, str]:
    if not mm_per_hour:
        return "none", "강우 없음"
    for threshold, key, label in RAIN_CLASSES:
        if mm_per_hour >= threshold:
            return key, label
    return "light", "약한 비"


# ---- observations ---------------------------------------------------------------------------------
@dataclass
class Snapshot:
    fetched_at: datetime
    interval: str
    observed: dict[str, tuple[datetime, float]] = field(default_factory=dict)


@dataclass
class _LiveState:
    snapshots: deque = field(default_factory=lambda: deque(maxlen=13))
    hourly: dict[str, tuple[datetime, float]] = field(default_factory=dict)
    hourly_fetched: datetime | None = None
    dams: list[dict[str, Any]] = field(default_factory=list)
    rainfall: list[dict[str, Any]] = field(default_factory=list)
    # 10-minute rain stays in memory while the server runs; hourly rain history is persisted separately.
    rain_slots: dict[str, dict[datetime, float]] = field(default_factory=dict)
    rain_hourly: dict[str, tuple[datetime, float]] = field(default_factory=dict)
    rain_hourly_history: dict[str, dict[datetime, float]] = field(default_factory=dict)
    rain_fetched_at: datetime | None = None
    rain_hourly_fetched: datetime | None = None
    rain_error: str | None = None
    last_error: str | None = None


_LIVE = _LiveState()
_LOCK = threading.Lock()


def _parse_stamp(value: str) -> datetime | None:
    value = (value or "").strip()
    try:
        return datetime.strptime(value if len(value) == 12 else value + "00", "%Y%m%d%H%M")
    except ValueError:
        return None


def _bulk(key: str, kind: str, interval: str, timeout: float = 20.0) -> list[dict[str, Any]]:
    response = httpx.get(BULK_ENDPOINT.format(key=key, kind=kind, interval=interval), timeout=timeout)
    response.raise_for_status()
    body = response.json()
    content = body.get("content") if isinstance(body, dict) else body
    return content if isinstance(content, list) else []


def _water_rows(rows: list[dict[str, Any]]) -> dict[str, tuple[datetime, float]]:
    observed: dict[str, tuple[datetime, float]] = {}
    for row in rows:
        stamp = _parse_stamp(row.get("ymdhm", ""))
        try:
            level = float(row.get("wl", ""))
        except (TypeError, ValueError):
            continue
        if stamp is not None and row.get("wlobscd"):
            observed[str(row["wlobscd"])] = (stamp, level)
    return observed


def _rain_rows(rows: list[dict[str, Any]]) -> dict[str, tuple[datetime, float]]:
    observed: dict[str, tuple[datetime, float]] = {}
    for row in rows:
        stamp = _parse_stamp(row.get("ymdhm", ""))
        try:
            value = float(row.get("rf", ""))
        except (TypeError, ValueError):
            continue  # a blank rf means the gauge has not reported this slot yet
        if stamp is not None and row.get("rfobscd") and value >= 0:
            observed[str(row["rfobscd"])] = (stamp, value)
    return observed


def _load_live_rain_hourly_history() -> dict[str, dict[datetime, float]]:
    """Restore recent hourly rain readings so a process restart does not erase the 12-hour window."""
    try:
        payload = json.loads(LIVE_RAIN_HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    now = datetime.now()
    cutoff = now - timedelta(hours=14)
    history: dict[str, dict[datetime, float]] = {}
    gauges = payload.get("gauges", {}) if isinstance(payload, dict) else {}
    if not isinstance(gauges, dict):
        return {}
    for code, samples in gauges.items():
        if not isinstance(code, str) or not isinstance(samples, list):
            continue
        slots: dict[datetime, float] = {}
        for sample in samples:
            try:
                stamp = datetime.fromisoformat(sample["at"]).replace(tzinfo=None)
                value = float(sample["mm"])
            except (KeyError, TypeError, ValueError):
                continue
            if cutoff <= stamp <= now + timedelta(minutes=5) and math.isfinite(value) and value >= 0:
                slots[stamp] = value
        if slots:
            history[code] = slots
    return history


def _persist_live_rain_hourly_history() -> None:
    payload = {
        "version": 1,
        "gauges": {
            code: [{"at": stamp.isoformat(), "mm": value} for stamp, value in sorted(slots.items())]
            for code, slots in sorted(_LIVE.rain_hourly_history.items()) if slots
        },
    }
    try:
        LIVE_RAIN_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = LIVE_RAIN_HISTORY_FILE.with_name(LIVE_RAIN_HISTORY_FILE.name + ".tmp")
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, LIVE_RAIN_HISTORY_FILE)
    except OSError:
        # Keep the in-memory window usable if the local cache directory is read-only.
        pass


def _store_live_rain_hourly(rows: list[dict[str, Any]]) -> None:
    observed = _rain_rows(rows)
    _LIVE.rain_hourly = observed
    changed = False
    for code, (stamp, value) in observed.items():
        slots = _LIVE.rain_hourly_history.setdefault(code, {})
        if slots.get(stamp) != value:
            slots[stamp] = value
            changed = True
        cutoff = stamp - timedelta(hours=14)
        for old in [moment for moment in slots if moment < cutoff]:
            slots.pop(old)
    if changed:
        _persist_live_rain_hourly_history()


_LIVE.rain_hourly_history = _load_live_rain_hourly_history()


def _store_live_rainfall(rows: list[dict[str, Any]], now: datetime) -> None:
    _LIVE.rainfall = rows
    for code, (stamp, value) in _rain_rows(rows).items():
        slots = _LIVE.rain_slots.setdefault(code, {})
        slots[stamp] = value
        for old in [moment for moment in slots if (stamp - moment).total_seconds() > 7200]:
            slots.pop(old)


def live_available() -> bool:
    from .llm_planner import _load_env_file_once  # imported here: llm_planner imports the agent tool catalogue

    _load_env_file_once()
    forced = os.environ.get("FLOODOPS_TWIN_MODE", "").strip().lower()
    return bool(os.environ.get("HRFCO_API_KEY")) and forced != "replay"


def refresh_live(force: bool = False) -> _LiveState:
    """Pull the bulk feeds at most every REFRESH_SECONDS. Errors keep the previous snapshot."""
    key = os.environ.get("HRFCO_API_KEY", "")
    now = datetime.now().replace(microsecond=0)
    with _LOCK:
        latest = _LIVE.snapshots[-1] if _LIVE.snapshots else None
        if not force and latest and (now - latest.fetched_at).total_seconds() < REFRESH_SECONDS:
            return _LIVE
        try:
            observed = _water_rows(_bulk(key, "waterlevel", "10M"))
            if observed:
                _LIVE.snapshots.append(Snapshot(now, "10M", observed))
            if _LIVE.hourly_fetched is None or (now - _LIVE.hourly_fetched).total_seconds() >= 3600:
                _LIVE.hourly = _water_rows(_bulk(key, "waterlevel", "1H"))
                _LIVE.hourly_fetched = now
            _LIVE.dams = _bulk(key, "dam", "10M")
            _store_live_rainfall(_bulk(key, "rainfall", "10M"), now)
            _LIVE.rain_fetched_at = now
            if _LIVE.rain_hourly_fetched is None or (now - _LIVE.rain_hourly_fetched).total_seconds() >= 3600:
                _store_live_rain_hourly(_bulk(key, "rainfall", "1H"))
                _LIVE.rain_hourly_fetched = now
            _LIVE.rain_error = None
            _LIVE.last_error = None
        except Exception as exc:  # the key sits in the URL; never surface it
            _LIVE.last_error = f"{type(exc).__name__} while refreshing the HRFCO bulk feed"
    return _LIVE


def refresh_live_rain(force: bool = False) -> _LiveState:
    """Refresh only rainfall feeds so a historical river replay can show current rain."""
    from .llm_planner import _load_env_file_once  # national_watch can be used without loading the agent first

    _load_env_file_once()
    key = os.environ.get("HRFCO_API_KEY", "")
    now = datetime.now().replace(microsecond=0)
    with _LOCK:
        if not force and _LIVE.rain_fetched_at and (now - _LIVE.rain_fetched_at).total_seconds() < REFRESH_SECONDS:
            return _LIVE
        if not key:
            _LIVE.rain_error = "HRFCO_API_KEY is not configured"
            _LIVE.rain_fetched_at = now
            return _LIVE
        try:
            _store_live_rainfall(_bulk(key, "rainfall", "10M", timeout=10.0), now)
            _LIVE.rain_fetched_at = now
            _LIVE.rain_error = None
        except Exception as exc:  # never expose the credential embedded in the URL
            _LIVE.rain_error = f"{type(exc).__name__} while refreshing the HRFCO rainfall feed"
            _LIVE.rain_fetched_at = now
            return _LIVE
        if _LIVE.rain_hourly_fetched is None or (now - _LIVE.rain_hourly_fetched).total_seconds() >= 3600:
            try:
                _store_live_rain_hourly(_bulk(key, "rainfall", "1H", timeout=10.0))
                _LIVE.rain_hourly_fetched = now
            except Exception as exc:  # the current 10-minute readings are still usable
                _LIVE.rain_error = f"{type(exc).__name__} while refreshing the HRFCO hourly rainfall feed"
    return _LIVE


def _hourly_file(code: str, kind: str = "waterlevel") -> Path:
    return HOURLY_DIR / f"{kind}_{code}_1H.csv"


def hourly_value(code: str, at_hour: str) -> float | None:
    return stored_value("waterlevel", code, at_hour)


@lru_cache(maxsize=8192)
def stored_value(kind: str, code: str, at_hour: str) -> float | None:
    """One stored hourly reading via mmap.find; the files are too large to load for 227 stations."""
    path = _hourly_file(code, kind)
    if not path.exists() or path.stat().st_size == 0:
        return None
    needle = f"{at_hour},{code},".encode()
    with path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as view:
        start = view.find(needle)
        if start < 0:
            return None
        end = view.find(b"\n", start)
        line = view[start:end if end > 0 else None].decode("utf-8", "replace").strip()
    value = line.split(",")[-1]
    try:
        return float(value)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def stored_station_codes() -> tuple[str, ...]:
    return tuple(sorted(path.name.split("_")[1] for path in HOURLY_DIR.glob("waterlevel_*_1H.csv")))


@lru_cache(maxsize=1)
def stored_rain_codes() -> tuple[str, ...]:
    return tuple(sorted(path.name.split("_")[1] for path in HOURLY_DIR.glob("rainfall_*_1H.csv")))


def _rain_reading(gauge: RainGauge, rain_10m: float | None, rain_1h: float | None, basis: str, time: datetime, window_end: datetime | None) -> dict[str, Any]:
    rate = rain_10m * 6 if rain_10m is not None else rain_1h
    key, label = rain_class(rate)
    return {"code": gauge.code, "name": gauge.name, "short_name": gauge.short_name, "region": gauge.region, "lon": gauge.lon, "lat": gauge.lat,
            "time": time.isoformat(), "rain_10m_mm": rain_10m, "rain_1h_mm": rain_1h, "rain_1h_basis": basis,
            "rain_1h_end": window_end.isoformat() if window_end else None,
            "intensity_mm_h": None if rate is None else round(rate, 1), "intensity": key, "intensity_label": label}


def rain_frame(at: str | None, live: bool | None = None) -> tuple[str, datetime | None, dict[str, dict[str, Any]]]:
    """Latest rain per gauge: (mode, observed time, readings). Live uses the 10-minute feed, replay the stored hours.

    `live` can select current rainfall independently of the river-level replay time.
    """
    gauges = rain_gauges()
    readings: dict[str, dict[str, Any]] = {}
    if live is None:
        live = not at and live_available()
    if not live:
        hour = (datetime.fromisoformat(at) if at else datetime.fromisoformat(DEFAULT_REPLAY_AT)).replace(minute=0, second=0, microsecond=0)
        for code in stored_rain_codes():
            value = stored_value("rainfall", code, hour.strftime("%Y-%m-%d %H:%M"))
            if value is not None and code in gauges:
                readings[code] = _rain_reading(gauges[code], None, value, "hourly", hour, hour)
        return "replay", hour if readings else None, readings
    state = refresh_live_rain()
    latest_stamp = max((max(slots) for slots in state.rain_slots.values() if slots), default=None)
    if latest_stamp is None or (datetime.now() - latest_stamp).total_seconds() > FRESH_MINUTES["10M"] * 60:
        return "live", None, readings
    for code, slots in state.rain_slots.items():
        if code not in gauges or not slots:
            continue
        stamp = max(slots)
        if (latest_stamp - stamp).total_seconds() > 1800:
            continue  # a gauge that stopped reporting is not "dry"
        window = [value for moment, value in slots.items() if 0 <= (stamp - moment).total_seconds() < 3600]
        if len(window) >= 6:
            rain_1h, basis, end = round(sum(window), 1), "rolling", stamp
        else:
            hourly = state.rain_hourly.get(code)
            rain_1h, basis, end = (hourly[1], "last_hour", hourly[0]) if hourly else (None, "none", None)
        readings[code] = _rain_reading(gauges[code], slots[stamp], rain_1h, basis, stamp, end)
    return "live", latest_stamp, readings


def nearby_rain(code: str, readings: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for rain_code, distance in rain_neighbours().get(code, ()):
        reading = readings.get(rain_code)
        if reading:
            return {key: reading[key] for key in ("code", "name", "short_name", "rain_10m_mm", "rain_1h_mm", "rain_1h_basis", "intensity_mm_h", "intensity", "intensity_label", "time")} | {"distance_km": distance}
    return None


def rain_summary(at: str | None = None, region: str | None = None, limit: int = 200, frame: tuple | None = None) -> dict[str, Any]:
    mode, observed, readings = frame or rain_frame(at)
    rows = [row for row in readings.values() if not region or row["region"] == region]
    by = {key: 0 for _, key, _ in RAIN_CLASSES}
    by["light"] = 0
    for row in rows:
        if row["intensity"] in by:
            by[row["intensity"]] += 1
    raining = sorted((row for row in rows if (row["intensity_mm_h"] or 0) > 0), key=lambda row: -(row["intensity_mm_h"] or 0))
    return {
        "available": bool(readings), "mode": mode, "observed_at": observed.isoformat() if observed else None,
        "error": _LIVE.rain_error if mode == "live" else None,
        "basis": "최근 10분 강우 × 6 (시간당 환산)" if mode == "live" else "저장된 1시간 강우",
        "gauges_total": len(rain_gauges()), "gauges_reporting": len(rows), "raining": len(raining),
        "heavy_or_above": by["heavy"] + by["very_heavy"], "by_intensity": by,
        "stations": raining[:limit], "limitations": RAIN_LIMITATIONS,
    }


def replay_snapshot(at: datetime) -> tuple[Snapshot, dict[str, tuple[datetime, float]]]:
    hour = at.replace(minute=0, second=0, microsecond=0)
    previous = hour - timedelta(hours=1)
    observed: dict[str, tuple[datetime, float]] = {}
    baseline: dict[str, tuple[datetime, float]] = {}
    for code in stored_station_codes():
        level = hourly_value(code, hour.strftime("%Y-%m-%d %H:%M"))
        if level is not None:
            observed[code] = (hour, level)
        earlier = hourly_value(code, previous.strftime("%Y-%m-%d %H:%M"))
        if earlier is not None:
            baseline[code] = (previous, earlier)
    return Snapshot(at, "1H", observed), baseline


# ---- assessment -----------------------------------------------------------------------------------
def classify_stage(level: float, levels: dict[str, float]) -> str:
    if not any(key in levels for key in ("attention", "advisory", "warning", "planned_flood")):
        return "unrated"
    stage = "normal"
    for name in ("attention", "advisory", "warning", "planned_flood"):
        if name in levels and level >= levels[name]:
            stage = name
    return stage


def rise_class(rate_per_10min: float | None) -> tuple[str, str]:
    if rate_per_10min is None:
        return "unknown", "불명"
    for threshold, key, label in RISE_CLASSES:
        if rate_per_10min >= threshold:
            return key, label
    return ("falling", "하강") if rate_per_10min <= -0.02 else ("steady", "정체")


def _baseline_for(code: str, latest: tuple[datetime, float], snapshots: list[Snapshot], hourly: dict[str, tuple[datetime, float]],
                  window_min: int = 30) -> tuple[datetime, float] | None:
    stamp = latest[0]
    for snap in reversed(snapshots):
        earlier = snap.observed.get(code)
        if earlier and (stamp - earlier[0]).total_seconds() >= window_min * 60:
            return earlier
    earlier = hourly.get(code)
    if earlier and earlier[0] < stamp:
        return earlier
    return None


def _previous_live_step(code: str, latest: tuple[datetime, float], snapshots: list[Snapshot]) -> tuple[datetime, float] | None:
    """Return the immediately previous distinct 10-minute reading, if no slot was skipped."""
    for snap in reversed(snapshots):
        earlier = snap.observed.get(code)
        if earlier is None:
            continue
        if earlier[0] > latest[0]:
            return None  # a source timestamp moved backwards; do not compare out of order
        if earlier[0] == latest[0]:
            continue  # refreshes can repeat the same 10-minute source reading
        return earlier if latest[0] - earlier[0] == timedelta(minutes=10) else None
    return None


def assess_station(station: Station, latest: tuple[datetime, float] | None, baseline: tuple[datetime, float] | None,
                   now: datetime, interval: str, quality_reference: tuple[datetime, float] | None = None) -> dict[str, Any]:
    links = facility_links().get(station.code, [])
    base = {
        "code": station.code, "name": station.name, "short_name": station.short_name, "agency": station.agency,
        "address": station.address, "region": station.region, "lon": station.lon, "lat": station.lat,
        "flood_forecast": station.flood_forecast, "levels_m": station.levels_m, "facilities": links,
        "tiers": {"operational": sum(1 for f in links if f["tier"] == "operational"), "watch": sum(1 for f in links if f["tier"] == "watch")},
    }
    if latest is None:
        return {**base, "observation": None, "quality": "missing", "stage": "unrated" if not station.levels_m else None,
                "stage_label": None, "rate_m_per_10min": None, "rate_window_min": None, "rise_class": "unknown", "rise_label": "불명",
                "margin_to_planned_flood_m": None, "minutes_to_planned_flood": None}
    stamp, level = latest
    age_min = int((now - stamp).total_seconds() // 60)
    quality = "fresh" if age_min <= FRESH_MINUTES.get(interval, 30) else "stale"
    rate = None
    window_min = None
    if baseline is not None:
        span = (stamp - baseline[0]).total_seconds() / 60
        if span > 0:
            rate = (level - baseline[1]) / span * 10
            window_min = int(round(span))
    if quality_reference is not None:
        expected_step = timedelta(minutes=10 if interval == "10M" else 60)
        if (stamp - quality_reference[0] == expected_step
                and abs(level - quality_reference[1]) >= STEP_SUSPECT_M):
            quality = "suspect"
    stage = classify_stage(level, station.levels_m)
    pfh = station.levels_m.get("planned_flood")
    margin = round(pfh - level, 2) if pfh is not None else None
    minutes = None
    if pfh is not None:
        if level >= pfh:
            minutes = 0
        elif rate is not None and rate > 0:
            minutes = int(round((pfh - level) / rate * 10))
    key, label = rise_class(rate)
    return {
        **base,
        "observation": {"time": stamp.isoformat(), "water_level_m": level, "interval": interval, "age_min": age_min},
        "quality": quality, "stage": stage, "stage_label": STAGE_KO[stage],
        "rate_m_per_10min": None if rate is None else round(rate, 3), "rate_window_min": window_min,
        "rise_class": key, "rise_label": label,
        "margin_to_planned_flood_m": margin, "minutes_to_planned_flood": minutes,
    }


def _priority(row: dict[str, Any]) -> tuple:
    stage_rank = STAGE_ORDER.index(row["stage"]) if row.get("stage") in STAGE_ORDER else -1
    minutes = row.get("minutes_to_planned_flood")
    return (-stage_rank, minutes if minutes is not None else 10**9, -(row.get("rate_m_per_10min") or 0))


def _frame(at: str | None) -> tuple[str, datetime, Snapshot, dict[str, tuple[datetime, float]], list[Snapshot], str | None]:
    """Pick live or stored observations and return (mode, now, latest snapshot, baselines, history, error)."""
    if at or not live_available():
        when = datetime.fromisoformat(at) if at else datetime.fromisoformat(DEFAULT_REPLAY_AT)
        snapshot, baseline = replay_snapshot(when)
        return "replay", when, snapshot, baseline, [], None
    state = refresh_live()
    if not state.snapshots:
        return "live", datetime.now().replace(microsecond=0), Snapshot(datetime.now(), "10M", {}), {}, [], state.last_error
    latest = state.snapshots[-1]
    return "live", datetime.now().replace(second=0, microsecond=0), latest, state.hourly, list(state.snapshots)[:-1], state.last_error


def _assess_all(at: str | None, region: str | None = None, rain_mode: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], tuple]:
    mode, now, snapshot, baselines, history, error = _frame(at)
    rain_live = mode == "live" if rain_mode is None else rain_mode == "live"
    rain = rain_frame(at, live=rain_live)
    rows = []
    for station in stations().values():
        if region and station.region != region:
            continue
        latest = snapshot.observed.get(station.code)
        if mode == "replay" and station.code not in stored_station_codes():
            continue
        baseline = (_baseline_for(station.code, latest, history, baselines) if latest and mode == "live" else baselines.get(station.code)) if latest else None
        quality_reference = (_previous_live_step(station.code, latest, history) if mode == "live" else baseline) if latest else None
        rows.append({**assess_station(station, latest, baseline, now, snapshot.interval, quality_reference), "rain_nearby": nearby_rain(station.code, rain[2])})
    observed_at = max((row["observation"]["time"] for row in rows if row["observation"]), default=None)
    meta = {
        "mode": mode, "at": now.isoformat(), "observed_at": observed_at, "fetched_at": snapshot.fetched_at.isoformat(),
        "interval": snapshot.interval, "stations_total": len(rows), "stations_observed": sum(1 for r in rows if r["observation"]),
        "source": "HRFCO OpenAPI bulk list (10M)" if mode == "live" else f"stored hourly series, {len(stored_station_codes())} flood-forecast stations",
        "error": error,
        "limitations": [
            "단계는 각 관측소의 공식 기준 수위(관심·주의보·경보·계획홍수위)로만 판정하며 시설 침수심이 아니다.",
            "연결 시설은 5 km 안 가장 가까운 관측소 기준이고 그 관측소가 시설 유입을 대표하는지는 검증하지 않았다(감시 등급).",
            "남은 분은 최근 상승 속도를 그대로 늘린 기준선이며 예보가 아니다.",
        ],
    }
    return meta, rows, rain


def overview(at: str | None = None, region: str | None = None, min_stage: str | None = None, limit: int = 300,
             rain_mode: str | None = None) -> dict[str, Any]:
    meta, rows, rain = _assess_all(at, region, rain_mode)
    floor = STAGE_ORDER.index(min_stage) if min_stage in STAGE_ORDER else -1
    counts = {stage: 0 for stage in STAGE_ORDER}
    quality = {"fresh": 0, "stale": 0, "suspect": 0, "missing": 0}
    rising = 0
    under_heavy_rain = 0
    regions: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("stage"):
            counts[row["stage"]] += 1
        quality[row["quality"]] += 1
        if (row.get("rate_m_per_10min") or 0) >= RISE_CLASSES[-1][0]:
            rising += 1
        if ((row.get("rain_nearby") or {}).get("intensity_mm_h") or 0) >= RAIN_CLASSES[1][0]:
            under_heavy_rain += 1
        bucket = regions.setdefault(row["region"], {"region": row["region"], "stations": 0, "max_stage": "unrated", "advisory_or_above": 0, "facilities": 0,
                                                    "raining": 0, "heavy_rain": 0})
        bucket["stations"] += 1
        bucket["facilities"] += len(row["facilities"])
        if row.get("stage") and STAGE_ORDER.index(row["stage"]) > STAGE_ORDER.index(bucket["max_stage"]):
            bucket["max_stage"] = row["stage"]
        if row.get("stage") and STAGE_ORDER.index(row["stage"]) >= STAGE_ORDER.index("advisory"):
            bucket["advisory_or_above"] += 1
    for reading in rain[2].values():
        bucket = regions.get(reading["region"])
        if bucket is None or not (reading["intensity_mm_h"] or 0) > 0:
            continue
        bucket["raining"] += 1
        if reading["intensity_mm_h"] >= RAIN_CLASSES[1][0]:
            bucket["heavy_rain"] += 1
    selected = [row for row in rows if floor < 0 or (row.get("stage") and STAGE_ORDER.index(row["stage"]) >= floor)]
    selected.sort(key=_priority)
    facilities_total = sum(len(row["facilities"]) for row in rows)
    return {
        **meta, "filter": {"region": region, "min_stage": min_stage},
        "counts": {"by_stage": counts, "quality": quality, "rising": rising, "facilities": facilities_total,
                   "facilities_operational": sum(1 for row in rows for f in row["facilities"] if f["tier"] == "operational"),
                   "under_heavy_rain": under_heavy_rain},
        "regions": sorted(regions.values(), key=lambda item: item["region"]),
        "rain": rain_summary(region=region, frame=rain),
        "stations": selected[:limit],
    }


def _rain_near_point(lon: float, lat: float, readings: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for reading in readings.values():
        if abs(reading["lat"] - lat) > 0.1 or abs(reading["lon"] - lon) > 0.13:
            continue
        distance = _km(lon, lat, reading["lon"], reading["lat"])
        if distance <= RAIN_LINK_KM and (best is None or distance < best[0]):
            best = (distance, reading)
    if best is None:
        return None
    reading = best[1]
    return {key: reading[key] for key in ("code", "name", "short_name", "rain_10m_mm", "rain_1h_mm", "rain_1h_basis", "intensity_mm_h", "intensity", "intensity_label", "time")} | {"distance_km": round(best[0], 1)}


def _facility_priority(row: dict[str, Any]) -> tuple:
    """관심 이상이면 단계 → 남은 분 순. 정상 이하에서는 남은 분(수천 분)이 의미가 없으므로 옆 강우가 먼저다."""
    stage_rank = STAGE_ORDER.index(row["stage"]) if row.get("stage") in STAGE_ORDER else 0
    elevated = stage_rank if stage_rank >= STAGE_ORDER.index("attention") else 0
    minutes = row.get("minutes_to_planned_flood")
    minutes = minutes if minutes is not None else 10**9
    rain = (row.get("rain_nearby") or {}).get("intensity_mm_h") or 0
    return (-elevated, minutes if elevated else 0, -rain, minutes, row["name"])


def facility_status(at: str | None = None, region: str | None = None, group: str | None = None, limit: int = 2000,
                    rain_mode: str | None = None) -> dict[str, Any]:
    """Each facility with the stage of the gauge standing in for it (if any) and the rain beside it."""
    meta, rows, rain = _assess_all(at, None, rain_mode)
    by_code = {row["code"]: row for row in rows}
    out = []
    for facility in facility_catalog():
        if region and facility["region"] != region or group and facility["group"] != group:
            continue
        gauge = by_code.get(facility["station_code"]) if facility["station_code"] else None
        item = {**facility, "gauge": None, "stage": None, "stage_label": "하천 관측소 없음" if not facility["station_code"] else "관측 없음",
                "minutes_to_planned_flood": None, "rate_m_per_10min": None, "rain_nearby": _rain_near_point(facility["lon"], facility["lat"], rain[2])}
        if gauge:
            item.update(gauge={key: gauge.get(key) for key in ("code", "name", "short_name", "observation", "quality", "levels_m", "rise_label", "flood_forecast")},
                        stage=gauge.get("stage"), stage_label=gauge.get("stage_label") or "기준 없음",
                        minutes_to_planned_flood=gauge.get("minutes_to_planned_flood"), rate_m_per_10min=gauge.get("rate_m_per_10min"))
        out.append(item)
    out.sort(key=_facility_priority)
    counts = {"total": len(out), "by_group": {key: sum(1 for f in out if f["group"] == key) for key in GROUP_KO},
              "by_tier": {key: sum(1 for f in out if f["tier"] == key) for key in ("operational", "watch", "rain_only")},
              "attention_or_above": sum(1 for f in out if f["stage"] in STAGE_ORDER[2:]),
              "advisory_or_above": sum(1 for f in out if f["stage"] in STAGE_ORDER[3:]),
              "under_heavy_rain": sum(1 for f in out if ((f["rain_nearby"] or {}).get("intensity_mm_h") or 0) >= RAIN_CLASSES[1][0])}
    return {"mode": meta["mode"], "at": meta["at"], "observed_at": meta["observed_at"], "filter": {"region": region, "group": group},
            "counts": counts, "facilities": out[:limit],
            "limitations": [
                "감시 등급 시설의 단계는 5 km 안 가장 가까운 하천 관측소의 단계이며, 그 관측소가 시설을 대표하는지는 검증하지 않았다.",
                "하천 관측소가 5 km 안에 없는 시설은 단계를 매기지 않고 10 km 안 강우만 보여준다.",
                "하천변 출입구는 OpenStreetMap 이름과 하천 선형 거리로 고른 후보이며 지자체 통제 대상 목록과 대조하지 않았다.",
                *RAIN_LIMITATIONS[:1],
            ]}


def station_detail(code: str, at: str | None = None, rain_mode: str | None = None) -> dict[str, Any]:
    station = stations().get(code)
    if station is None:
        raise KeyError(f"Unknown station: {code}")
    mode, now, snapshot, baselines, history, error = _frame(at)
    latest = snapshot.observed.get(code)
    baseline = (_baseline_for(code, latest, history, baselines) if latest and mode == "live" else baselines.get(code)) if latest else None
    quality_reference = (_previous_live_step(code, latest, history) if mode == "live" else baseline) if latest else None
    rain_live = mode == "live" if rain_mode is None else rain_mode == "live"
    row = {**assess_station(station, latest, baseline, now, snapshot.interval, quality_reference), "rain_nearby": nearby_rain(code, rain_frame(at, live=rain_live)[2])}
    series = [{"time": snap.observed[code][0].isoformat(), "water_level_m": snap.observed[code][1]} for snap in [*history, snapshot] if code in snap.observed]
    if mode == "replay":
        series = []
        for back in range(24, -1, -1):
            hour = (now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=back))
            level = hourly_value(code, hour.strftime("%Y-%m-%d %H:%M"))
            if level is not None:
                series.append({"time": hour.isoformat(), "water_level_m": level})
    return {**row, "mode": mode, "at": now.isoformat(), "recent": series, "error": error}


def changes(since_min: int = 60, at: str | None = None, region: str | None = None) -> dict[str, Any]:
    """Stage moves and new risers between the latest snapshot and one at least `since_min` older."""
    mode, now, snapshot, baselines, history, error = _frame(at)
    if mode == "replay":
        earlier_at = now - timedelta(minutes=since_min)
        earlier, _ = replay_snapshot(earlier_at)
    else:
        earlier = next((snap for snap in reversed(history) if (snapshot.fetched_at - snap.fetched_at).total_seconds() >= since_min * 60), None)
    if earlier is None:
        return {"mode": mode, "at": now.isoformat(), "since_min": since_min, "available": False,
                "note": "비교할 이전 스냅샷이 아직 없습니다. 감시가 시작된 뒤 시간이 더 지나야 합니다.", "stage_up": [], "stage_down": [], "new_rising": []}
    up, down, rising = [], [], []
    for station in stations().values():
        if region and station.region != region:
            continue
        now_obs, then_obs = snapshot.observed.get(station.code), earlier.observed.get(station.code)
        if not now_obs or not then_obs:
            continue
        stage_now, stage_then = classify_stage(now_obs[1], station.levels_m), classify_stage(then_obs[1], station.levels_m)
        delta = now_obs[1] - then_obs[1]
        span = max(1.0, (now_obs[0] - then_obs[0]).total_seconds() / 60)
        item = {"code": station.code, "name": station.name, "region": station.region, "from": stage_then, "to": stage_now,
                "delta_m": round(delta, 2), "rate_m_per_10min": round(delta / span * 10, 3), "facilities": len(facility_links().get(station.code, []))}
        if STAGE_ORDER.index(stage_now) > STAGE_ORDER.index(stage_then):
            up.append(item)
        elif STAGE_ORDER.index(stage_now) < STAGE_ORDER.index(stage_then):
            down.append(item)
        elif delta / span * 10 >= RISE_CLASSES[1][0]:
            rising.append(item)
    for bucket in (up, down, rising):
        bucket.sort(key=lambda item: -abs(item["delta_m"]))
    return {"mode": mode, "at": now.isoformat(), "compared_to": earlier.fetched_at.isoformat(), "since_min": since_min, "available": True,
            "stage_up": up[:20], "stage_down": down[:20], "new_rising": rising[:20]}


def regions_summary(at: str | None = None) -> list[dict[str, Any]]:
    return overview(at)["regions"]


def find_station(text: str) -> Station | None:
    """A station the user named: catalogue code, the name in parentheses, or the full name."""
    candidates = []
    for station in stations().values():
        if station.code in text:
            return station
        short = station.short_name
        if len(short) >= 2 and short in text:
            candidates.append((len(short), station))
        elif station.name in text:
            candidates.append((len(station.name), station))
    if not candidates:
        return None
    candidates.sort(key=lambda item: -item[0])
    return candidates[0][1]


def find_facility(text: str) -> dict[str, Any] | None:
    best = None
    for facility in facility_index().values():
        name = facility["name"]
        if len(name) >= 2 and name in text and (best is None or len(name) > len(best["name"])):
            best = facility
    return best

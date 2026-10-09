"""Collect nationwide station catalogs and historical series from the HRFCO OpenAPI.

The Han River Flood Control Office OpenAPI (api.hrfco.go.kr) serves every national hydrologic station
with one free key: water level (1,420 stations), rainfall (744), dams and weirs. One request returns a
whole year of hourly values or 15 days of 10-minute values, so a real-station training set for the
water-level-rise model can be built from the original provider instead of the anonymised contest data.

    python data/scripts/collect_hrfco_history.py catalog
    python data/scripts/collect_hrfco_history.py nearest --lon 127.3376 --lat 36.6246 --kind rainfall --limit 5
    python data/scripts/collect_hrfco_history.py fetch --kind waterlevel --stations 3011665 3011635 3011685 \
        --interval 1H --years 2019-2026
    python data/scripts/collect_hrfco_history.py fetch --kind rainfall --stations 30114020 --interval 10M \
        --years 2019-2026 --months 6-9

Raw responses go to data/raw/hrfco/ (git-ignored); merged per-station CSVs go to data/processed/hrfco/;
every fetch is recorded in data/manifests/hrfco-history.json with row counts and SHA-256.
The key is read from HRFCO_API_KEY (repository .env) and never written to disk.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw" / "hrfco"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "hrfco"
CATALOG_FILE = REPO_ROOT / "data" / "manifests" / "hrfco-stations.json"
HISTORY_MANIFEST = REPO_ROOT / "data" / "manifests" / "hrfco-history.json"
BASE = "https://api.hrfco.go.kr/{key}"
CODE_FIELD = {"waterlevel": "wlobscd", "rainfall": "rfobscd", "dam": "dmobscd", "bo": "boobscd"}
VALUE_FIELD = {"waterlevel": "wl", "rainfall": "rf"}
PAUSE_SECONDS = 0.35


def load_key() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env", override=False)
    except ImportError:
        pass
    key = os.environ.get("HRFCO_API_KEY", "").strip()
    if not key:
        sys.exit("HRFCO_API_KEY is not set (put it in the repository .env)")
    return key


def get_json(key: str, path: str, retries: int = 3) -> dict[str, Any]:
    url = f"{BASE.format(key=key)}/{path}"
    for attempt in range(retries):
        try:
            response = httpx.get(url, timeout=90)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"HRFCO request failed for {path}: {type(exc).__name__}") from exc
            time.sleep(2 * (attempt + 1))
    return {}


def dms_to_decimal(value: str | None) -> float | None:
    if not value:
        return None
    parts = [p for p in re.split(r"[-:\s]+", value.strip()) if p]
    if not parts:
        return None
    try:
        d, m, s = (float(parts[0]), float(parts[1]) if len(parts) > 1 else 0.0, float(parts[2]) if len(parts) > 2 else 0.0)
    except ValueError:
        return None
    return round(d + m / 60 + s / 3600, 6)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


# ---- catalog ------------------------------------------------------------------------------------
def build_catalog(key: str) -> dict[str, Any]:
    catalog: dict[str, Any] = {"source": "HRFCO OpenAPI (api.hrfco.go.kr)", "fetched_at": datetime.now().isoformat(timespec="seconds"), "kinds": {}}
    for kind, code_field in CODE_FIELD.items():
        rows = [r for r in get_json(key, f"{kind}/info.json").get("content", []) if isinstance(r, dict)]
        stations = []
        for row in rows:
            stations.append({
                "code": row.get(code_field),
                "name": row.get("obsnm"),
                "agency": row.get("agcnm"),
                "address": (row.get("addr") or "").strip(),
                "address_detail": (row.get("etcaddr") or "").strip(),
                "lon": dms_to_decimal(row.get("lon")),
                "lat": dms_to_decimal(row.get("lat")),
                **({k: _num(row.get(k)) for k in ("gdt", "attwl", "wrnwl", "almwl", "srswl", "pfh") if k in row}),
                **({"flood_forecast_station": row.get("fstnyn")} if "fstnyn" in row else {}),
            })
        agencies: dict[str, int] = {}
        for s in stations:
            agencies[s["agency"] or "?"] = agencies.get(s["agency"] or "?", 0) + 1
        catalog["kinds"][kind] = {"count": len(stations), "agencies": agencies, "stations": stations}
        time.sleep(PAUSE_SECONDS)
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    return catalog


def _num(value: Any) -> float | None:
    try:
        return float(str(value).strip()) if str(value).strip() else None
    except ValueError:
        return None


def nearest(kind: str, lon: float, lat: float, limit: int) -> list[dict[str, Any]]:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    stations = [s for s in catalog["kinds"][kind]["stations"] if s["lon"] and s["lat"]]
    def dist(s: dict[str, Any]) -> float:
        dx = (s["lon"] - lon) * 111.32 * math.cos(math.radians(lat))
        dy = (s["lat"] - lat) * 110.57
        return math.hypot(dx, dy)
    ranked = sorted(stations, key=dist)[:limit]
    return [{**s, "distance_km": round(dist(s), 2)} for s in ranked]


# ---- series -------------------------------------------------------------------------------------
def _chunks(year: int, months: tuple[int, int], interval: str) -> Iterable[tuple[str, str, str]]:
    """(label, start, end) request windows: one call per year for 1H, 15-day windows for 10M."""
    m0, m1 = months
    start = date(year, m0, 1)
    end = date(year + 1, 1, 1) - timedelta(days=1) if m1 == 12 else date(year, m1 + 1, 1) - timedelta(days=1)
    if interval == "1H":
        yield (f"{year}", f"{start:%Y%m%d}00", f"{end:%Y%m%d}23")
        return
    cursor = start
    while cursor <= end:
        stop = min(cursor + timedelta(days=14), end)
        yield (f"{year}_{cursor:%m%d}", f"{cursor:%Y%m%d}0000", f"{stop:%Y%m%d}2350")
        cursor = stop + timedelta(days=1)


def fetch_series(key: str, kind: str, station: str, interval: str, years: list[int], months: tuple[int, int]) -> dict[str, Any]:
    value_field = VALUE_FIELD[kind]
    raw_dir = RAW_DIR / kind / station
    raw_dir.mkdir(parents=True, exist_ok=True)
    merged: dict[str, str] = {}
    requests = 0
    for year in years:
        for label, start, end in _chunks(year, months, interval):
            raw_file = raw_dir / f"{interval}_{label}.json"
            if raw_file.exists():
                payload = json.loads(raw_file.read_text(encoding="utf-8"))
            else:
                payload = get_json(key, f"{kind}/list/{interval}/{station}/{start}/{end}.json")
                raw_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                requests += 1
                time.sleep(PAUSE_SECONDS)
            for row in payload.get("content", []):
                stamp = str(row.get("ymdhm", "")).strip()
                value = str(row.get(value_field, "")).strip()
                if stamp:
                    merged[stamp] = value
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / f"{kind}_{station}_{interval}.csv"
    valid = 0
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp_kst", "station_id", value_field])
        for stamp in sorted(merged):
            ts = datetime.strptime(stamp if len(stamp) == 12 else stamp + "00", "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
            writer.writerow([ts, station, merged[stamp]])
            valid += bool(merged[stamp])
    by_year: dict[str, dict[str, int]] = {}
    for stamp, value in merged.items():
        y = stamp[:4]
        by_year.setdefault(y, {"rows": 0, "valid": 0})
        by_year[y]["rows"] += 1
        by_year[y]["valid"] += bool(value)
    return {
        "kind": kind, "station": station, "interval": interval, "years": years, "months": list(months),
        "rows": len(merged), "valid": valid, "by_year": by_year, "requests": requests,
        "processed_file": str(out.relative_to(REPO_ROOT)).replace("\\", "/"), "sha256": sha256(out),
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }


def record(entry: dict[str, Any]) -> None:
    manifest = json.loads(HISTORY_MANIFEST.read_text(encoding="utf-8")) if HISTORY_MANIFEST.exists() else {"source": "HRFCO OpenAPI", "entries": []}
    manifest["entries"] = [e for e in manifest["entries"] if not (e["kind"] == entry["kind"] and e["station"] == entry["station"] and e["interval"] == entry["interval"])]
    manifest["entries"].append(entry)
    HISTORY_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


def qc_jumps(kind: str, station: str, interval: str, jump_m: float) -> dict[str, Any]:
    """Flag water-level steps larger than jump_m between consecutive samples (sensor or datum glitches)."""

    path = PROCESSED_DIR / f"{kind}_{station}_{interval}.csv"
    rows = [r for r in csv.DictReader(path.open(encoding="utf-8")) if r.get(VALUE_FIELD[kind])]
    flags = []
    prev: tuple[str, float] | None = None
    for row in rows:
        value = float(row[VALUE_FIELD[kind]])
        if prev and abs(value - prev[1]) >= jump_m:
            flags.append({"time": row["timestamp_kst"], "from": prev[1], "to": value})
        prev = (row["timestamp_kst"], value)
    result = {"kind": kind, "station": station, "interval": interval, "jump_threshold_m": jump_m, "flag_count": len(flags), "flags": flags[:50]}
    manifest = json.loads(HISTORY_MANIFEST.read_text(encoding="utf-8"))
    for entry in manifest["entries"]:
        if entry["kind"] == kind and entry["station"] == station and entry["interval"] == interval:
            entry["qc_jumps"] = result
    HISTORY_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


EVENTS_FILE = REPO_ROOT / "data" / "manifests" / "hrfco-events.json"


def summarize_events(interval: str = "1H", gap_hours: int = 24) -> dict[str, Any]:
    """Count flood events per downloaded water-level station against its official levels.

    An event is a run of samples at or above the attention level (attwl) separated by more than
    gap_hours. The peak level is compared with the advisory (wrnwl), warning (almwl) and planned
    flood (pfh) levels from the station catalog, so the training-set size per station is visible.
    """

    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    levels = {s["code"]: s for s in catalog["kinds"]["waterlevel"]["stations"]}
    summary: dict[str, Any] = {"interval": interval, "gap_hours": gap_hours, "built_at": datetime.now().isoformat(timespec="seconds"), "stations": {}}
    for path in sorted(PROCESSED_DIR.glob(f"waterlevel_*_{interval}.csv")):
        code = path.stem.split("_")[1]
        info = levels.get(code, {})
        att, wrn, alm, pfh = (info.get(k) for k in ("attwl", "wrnwl", "almwl", "pfh"))
        rows = [r for r in csv.DictReader(path.open(encoding="utf-8")) if r.get("wl")]
        values = [(datetime.strptime(r["timestamp_kst"], "%Y-%m-%d %H:%M"), float(r["wl"])) for r in rows]
        events: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        if att is not None:
            for t, w in values:
                if w >= att:
                    if current is None or (t - current["end_dt"]).total_seconds() > gap_hours * 3600:
                        if current:
                            events.append(current)
                        current = {"start": t.strftime("%Y-%m-%d %H:%M"), "end": t.strftime("%Y-%m-%d %H:%M"), "end_dt": t, "peak": w, "peak_time": t.strftime("%Y-%m-%d %H:%M")}
                    else:
                        current["end"] = t.strftime("%Y-%m-%d %H:%M")
                        current["end_dt"] = t
                        if w > current["peak"]:
                            current["peak"], current["peak_time"] = w, t.strftime("%Y-%m-%d %H:%M")
            if current:
                events.append(current)
        for e in events:
            e.pop("end_dt", None)
        summary["stations"][code] = {
            "name": info.get("name"), "agency": info.get("agency"), "flood_forecast_station": info.get("flood_forecast_station"),
            "levels_m": {"attention": att, "advisory": wrn, "warning": alm, "planned_flood": pfh},
            "rows": len(rows), "first": rows[0]["timestamp_kst"] if rows else None, "last": rows[-1]["timestamp_kst"] if rows else None,
            "max_wl_m": max((w for _, w in values), default=None),
            "events_attention": len(events),
            "events_advisory": sum(1 for e in events if wrn is not None and e["peak"] >= wrn),
            "events_warning": sum(1 for e in events if alm is not None and e["peak"] >= alm),
            "events_planned_flood": sum(1 for e in events if pfh is not None and e["peak"] >= pfh),
            "events": events[:40],
        }
    totals = {k: sum(v[k] for v in summary["stations"].values()) for k in ("events_attention", "events_advisory", "events_warning", "events_planned_flood")}
    summary["totals"] = {"stations": len(summary["stations"]), **totals}
    EVENTS_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def parse_years(text: str) -> list[int]:
    if "-" in text:
        a, b = text.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(t) for t in text.split(",")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="download the nationwide station catalogs")
    near = sub.add_parser("nearest", help="list the nearest stations to a point")
    near.add_argument("--kind", default="rainfall", choices=list(CODE_FIELD))
    near.add_argument("--lon", type=float, required=True)
    near.add_argument("--lat", type=float, required=True)
    near.add_argument("--limit", type=int, default=5)
    fetch = sub.add_parser("fetch", help="download historical series for stations")
    fetch.add_argument("--kind", default="waterlevel", choices=list(VALUE_FIELD))
    fetch.add_argument("--stations", nargs="+", required=True)
    fetch.add_argument("--interval", default="1H", choices=["1H", "10M"])
    fetch.add_argument("--years", default="2019-2026")
    fetch.add_argument("--months", default="1-12", help="e.g. 6-9 for the flood season")
    qc = sub.add_parser("qc", help="flag implausible jumps in downloaded water-level series")
    qc.add_argument("--kind", default="waterlevel", choices=list(VALUE_FIELD))
    qc.add_argument("--stations", nargs="+", required=True)
    qc.add_argument("--interval", default="1H", choices=["1H", "10M"])
    qc.add_argument("--jump", type=float, default=3.0, help="flag steps of at least this many metres between samples")
    ev = sub.add_parser("events", help="count flood events per downloaded water-level station against official levels")
    ev.add_argument("--interval", default="1H", choices=["1H", "10M"])
    ev.add_argument("--gap-hours", type=int, default=24)
    args = parser.parse_args()
    if args.command == "events":
        out = summarize_events(args.interval, args.gap_hours)
        print(json.dumps(out["totals"], ensure_ascii=False))
        return
    if args.command == "qc":
        for station in args.stations:
            out = qc_jumps(args.kind, station, args.interval, args.jump)
            print(json.dumps({k: out[k] for k in ("station", "interval", "flag_count")} | {"first_flags": out["flags"][:4]}, ensure_ascii=False))
        return
    key = load_key()
    if args.command == "catalog":
        catalog = build_catalog(key)
        print(json.dumps({k: {"count": v["count"], "agencies": v["agencies"]} for k, v in catalog["kinds"].items()}, ensure_ascii=False, indent=1))
    elif args.command == "nearest":
        print(json.dumps(nearest(args.kind, args.lon, args.lat, args.limit), ensure_ascii=False, indent=1))
    else:
        m0, m1 = (int(x) for x in args.months.split("-"))
        for station in args.stations:
            entry = fetch_series(key, args.kind, station, args.interval, parse_years(args.years), (m0, m1))
            record(entry)
            print(json.dumps({k: entry[k] for k in ("kind", "station", "interval", "rows", "valid", "requests", "processed_file")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

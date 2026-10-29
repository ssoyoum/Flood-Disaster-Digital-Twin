"""Collect KMA AWS rain around one facility for a past event window (API hub `nph-aws2_min`).

    python data/scripts/collect_kma_aws_event.py --event busan-choryang-2020-07-23 \
        --lat 35.119110 --lon 129.044801 --start 2020-07-23T18:00 --end 2020-07-24T00:00

Each request returns one minute snapshot for every station; only stations within --radius-km of the point are
kept. RN-15m / RN-60m / RN-DAY are KMA's own running totals at that minute, so a 10-minute step can still miss
the true 60-minute peak between samples. Missing values stay empty; nothing is filled or interpolated.
The key is read by backend/app/kma_aws.py and never written to the outputs.

Output: data/processed/kma/events/{event}_aws.csv and data/manifests/kma-aws-events/{event}.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import kma_aws  # noqa: E402

OUT_DIR = ROOT / "data" / "processed" / "kma" / "events"
MANIFEST_DIR = ROOT / "data" / "manifests" / "kma-aws-events"


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event", required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--start", required=True, help="KST, e.g. 2020-07-23T18:00")
    parser.add_argument("--end", required=True)
    parser.add_argument("--step-min", type=int, default=10)
    parser.add_argument("--radius-km", type=float, default=5.0)
    args = parser.parse_args()

    site = (args.lat, args.lon)
    near = {s["stn"]: round(km(site, (s["lat"], s["lon"])), 2) for s in kma_aws.stations().values()
            if km(site, (s["lat"], s["lon"])) <= args.radius_km}
    if not near:
        sys.exit(f"no AWS station within {args.radius_km} km")
    names = {stn: kma_aws.stations()[stn]["name"] for stn in near}

    rows, failures = [], []
    at, end = datetime.fromisoformat(args.start), datetime.fromisoformat(args.end)
    while at <= end:
        result = kma_aws.fetch(at=at)
        if not result["available"]:
            failures.append({"at": at.isoformat(timespec="minutes"), "error": result["error"]})
        else:
            for stn, dist in sorted(near.items(), key=lambda kv: kv[1]):
                r = result["rows"].get(stn) or {}
                rows.append({"requested_at": at.isoformat(timespec="minutes"), "stn": stn, "name": names[stn], "distance_km": dist,
                             "observed_at": r.get("time", ""),
                             **{k: "" if r.get(k) is None else r[k] for k in ("rain_15m_mm", "rain_1h_mm", "rain_day_mm")}})
        at += timedelta(minutes=args.step_min)
        time.sleep(0.2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.event}_aws.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    peaks = {}
    for stn in near:
        series = [r for r in rows if r["stn"] == stn and r["rain_1h_mm"] != ""]
        top = max(series, key=lambda r: r["rain_1h_mm"], default=None)
        top15 = max((r for r in rows if r["stn"] == stn and r["rain_15m_mm"] != ""), key=lambda r: r["rain_15m_mm"], default=None)
        peaks[stn] = {"name": names[stn], "distance_km": near[stn],
                      "max_sampled_rain_1h_mm": top["rain_1h_mm"] if top else None, "at": top["requested_at"] if top else None,
                      "max_sampled_rain_15m_mm": top15["rain_15m_mm"] if top15 else None, "at_15m": top15["requested_at"] if top15 else None,
                      "missing_samples": sum(1 for r in rows if r["stn"] == stn and r["rain_1h_mm"] == "")}
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "event": args.event, "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "KMA API hub nph-aws2_min (typ01), stn=0 snapshot per request",
        "point": {"lat": args.lat, "lon": args.lon}, "radius_km": args.radius_km,
        "window_kst": {"start": args.start, "end": args.end, "step_min": args.step_min},
        "requests_failed": failures, "rows": len(rows),
        "sampled_peaks": peaks,
        "note": "Peaks are the largest KMA running totals at the sampled minutes, not the true continuous maximum.",
        "output": {"path": out.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(out.read_bytes()).hexdigest()},
    }
    (MANIFEST_DIR / f"{args.event}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

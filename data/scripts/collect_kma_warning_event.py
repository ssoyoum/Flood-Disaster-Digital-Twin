"""Collect the KMA heavy-rain alert commands for chosen warning zones over a past event window.

    python data/scripts/collect_kma_warning_event.py --event osong-2023 --area 청주시 \
        --start 2023-07-14T00:00 --end 2023-07-15T09:00

`wrn_now_data.php?tm=` returns the alerts in effect at that minute; the issuance log (`wrn_met_data.php`)
is not approved for this key. Each sample keeps the zone's latest command and its TM_FC, so a change that starts and
ends between two samples is missed, but every change visible at a sample keeps its exact issue minute. A command
announced for a later minute is kept with in_effect=false. Level "none" means no heavy-rain row for the zone, not
missing data; requests are retried three times and the remaining failures are listed separately.

Output: data/processed/kma/events/{event}_warnings.csv and data/manifests/kma-warning-events/{event}.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import kma_weather_warning as w  # noqa: E402

OUT_DIR = ROOT / "data" / "processed" / "kma" / "events"
MANIFEST_DIR = ROOT / "data" / "manifests" / "kma-warning-events"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event", required=True)
    parser.add_argument("--area", action="append", required=True, help="REG_KO warning zone name, repeatable")
    parser.add_argument("--start", required=True, help="KST, e.g. 2023-07-14T00:00")
    parser.add_argument("--end", required=True)
    parser.add_argument("--step-min", type=int, default=10)
    args = parser.parse_args()

    rows, failures = [], []
    at, end = datetime.fromisoformat(args.start), datetime.fromisoformat(args.end)
    while at <= end:
        for attempt in range(3):
            result = w.at(at)
            if result["available"]:
                break
            time.sleep(2 * (attempt + 1))
        if not result["available"]:
            failures.append({"at": at.isoformat(timespec="minutes"), "error": result["error"]})
        else:
            hits = {r["area"]: r for r in result["rows"] if r["area"] in args.area}
            for area in args.area:
                r = hits.get(area)
                rows.append({"sampled_at": at.isoformat(timespec="minutes"), "area": area,
                             "province": r["province"] if r else "", "region_code": r["region_code"] if r else "",
                             "level": r["level"] if r else "none", "level_ko": r["level_ko"] if r else "",
                             "issued_at": r["issued_at"] if r else "", "effective_at": r["effective_at"] if r else "",
                             "in_effect": ("true" if r["in_effect"] else "false") if r else "", "command": r["command"] if r else ""})
        at += timedelta(minutes=args.step_min)
        time.sleep(0.2)
    if not rows:
        sys.exit(f"no successful samples: {failures[:3]}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.event}_warnings.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    changes = []
    for area in args.area:
        previous = None
        for r in (r for r in rows if r["area"] == area):
            state = (r["level"], r["issued_at"], r["in_effect"])
            if state != previous:
                changes.append({"area": area, "first_sampled_at": r["sampled_at"], "level": r["level"], "level_ko": r["level_ko"],
                                "issued_at": r["issued_at"], "effective_at": r["effective_at"], "in_effect": r["in_effect"],
                                "command": r["command"]})
                previous = state
    manifest = {
        "event": args.event, "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "KMA API hub wrn_now_data.php with tm (alerts in effect at that minute)",
        "areas": args.area, "window_kst": {"start": args.start, "end": args.end, "step_min": args.step_min},
        "samples": len(rows), "requests_failed": failures, "changes": changes,
        "note": "issued_at is KMA TM_FC of the zone's latest command. in_effect=false means that command takes effect later; "
                "the alert it replaces is not returned, so the level in effect during that gap is unknown. "
                "level 'none' means no heavy-rain row for the zone.",
        "output": {"path": out.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(out.read_bytes()).hexdigest()},
    }
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    (MANIFEST_DIR / f"{args.event}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("event", "samples", "requests_failed", "changes")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

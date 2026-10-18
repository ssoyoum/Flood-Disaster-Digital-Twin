"""Collect official flood forecast issuances (홍수주의보·홍수경보 발령·변경·해제) from the HRFCO OpenAPI.

`fldfct/list/{yyyyMMdd}` returns the issuances of one day for every flood control office. They are the
official counterpart of FloodOps' review rule: comparing when the office issued a warning at a gauge with
when the rule would have recommended a review gives the rule's lead (or lag) over the existing system.

    python data/scripts/collect_flood_forecast_issuance.py --years 2019-2026 --months 5-10
    python data/scripts/collect_flood_forecast_issuance.py --offline     # rebuild the CSV from saved days

Outputs:
- data/raw/hrfco_fldfct/fldfct_{yyyyMMdd}.json        one raw response per day (gitignored)
- data/processed/flood_forecast/flood_forecast_issuances.csv   one row per issuance, deduplicated
- data/processed/flood_forecast/flood_forecast_summary.json    counts by year, kind and office

Needs HRFCO_API_KEY (environment or the repository .env). The key sits in the request path; it is never
printed or written to disk.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "hrfco_fldfct"
OUT = ROOT / "data" / "processed" / "flood_forecast"
ENDPOINT = "https://api.hrfco.go.kr/{key}/fldfct/list/{day}.json"
FIELDS = ["issued_at", "kind", "number", "office", "station_code", "station_name", "river", "warning_area", "warning_river",
          "level_at_issue_m", "level_time", "trend", "forecast_level_m", "forecast_time", "notes", "source_day"]


def load_key() -> str:
    key = os.environ.get("HRFCO_API_KEY", "").strip()
    if key:
        return key
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("HRFCO_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("HRFCO_API_KEY is not set.")


def span(text: str) -> list[int]:
    start, _, end = text.partition("-")
    return list(range(int(start), int(end or start) + 1))


def fetch_day(key: str, day: date) -> list[dict]:
    raw = RAW / f"fldfct_{day:%Y%m%d}.json"
    if raw.exists():
        return json.loads(raw.read_text(encoding="utf-8"))
    url = ENDPOINT.format(key=key, day=f"{day:%Y%m%d}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == 2:
                print(f"  {day}: {type(exc).__name__} (skipped)", flush=True)
                return []
            time.sleep(2 + attempt * 3)
    rows = body.get("content") if isinstance(body, dict) else body
    rows = rows if isinstance(rows, list) else []  # code 990 = no issuance that day
    RAW.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.15)
    return rows


def stamp(value: str) -> str:
    value = (value or "").strip()
    try:
        return datetime.strptime(value, "%Y%m%d%H%M").isoformat(timespec="minutes")
    except ValueError:
        return ""


def number(value: str) -> str:
    value = (value or "").strip()
    try:
        return f"{float(value):g}"
    except ValueError:
        return ""


def normalise(row: dict, day: date) -> dict:
    return {
        "issued_at": stamp(row.get("ancdt", "")), "kind": (row.get("kind") or "").strip(), "number": (row.get("no") or "").strip(),
        "office": (row.get("ancnm") or "").strip(), "station_code": (row.get("sttnm") or "").strip(), "station_name": (row.get("obsnm") or "").strip(),
        "river": (row.get("rvrnm") or "").strip(), "warning_area": (row.get("wrnaranm") or "").strip(), "warning_river": (row.get("wrnrvrnm") or "").strip(),
        "level_at_issue_m": number(row.get("sttcurhgt", "")), "level_time": stamp(row.get("sttcurdt", "")), "trend": (row.get("sttcurcng") or "").strip(),
        "forecast_level_m": number(row.get("sttfcthgt", "") or row.get("fcthgt", "")), "forecast_time": stamp(row.get("sttfctdt", "") or row.get("fctdt", "")),
        "notes": " ".join((row.get("rfrnc2") or "").split()), "source_day": f"{day:%Y-%m-%d}",
    }


def days(years: list[int], months: list[int]) -> list[date]:
    today = date.today()
    out = []
    for year in years:
        for month in months:
            for d in range(1, calendar.monthrange(year, month)[1] + 1):
                day = date(year, month, d)
                if day <= today:
                    out.append(day)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--years", default="2019-2026")
    parser.add_argument("--months", default="5-10", help="flood season months; 1-12 for every day")
    parser.add_argument("--offline", action="store_true", help="only rebuild from saved raw days")
    args = parser.parse_args()
    key = "" if args.offline else load_key()
    rows: dict[tuple, dict] = {}
    targets = days(span(args.years), span(args.months))
    for index, day in enumerate(targets, 1):
        raw = RAW / f"fldfct_{day:%Y%m%d}.json"
        if args.offline and not raw.exists():
            continue
        for row in fetch_day(key, day):
            item = normalise(row, day)
            rows[(item["number"], item["kind"], item["station_code"], item["issued_at"])] = item
        if index % 60 == 0:
            print(f"  {index}/{len(targets)} days, {len(rows)} issuances", flush=True)
    ordered = sorted(rows.values(), key=lambda r: (r["issued_at"], r["station_code"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "flood_forecast_issuances.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ordered)
    summary = {
        "built_at": datetime.now().isoformat(timespec="seconds"), "source": "HRFCO OpenAPI fldfct/list/{yyyyMMdd}",
        "years": args.years, "months": args.months, "days_requested": len(targets), "issuances": len(ordered),
        "by_year": dict(sorted(Counter(r["issued_at"][:4] for r in ordered).items())),
        "by_kind": dict(Counter(r["kind"] for r in ordered).most_common()),
        "by_office": dict(Counter(r["office"] for r in ordered).most_common()),
        "stations": len({r["station_code"] for r in ordered}),
    }
    (OUT / "flood_forecast_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

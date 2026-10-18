"""Collect Seoul river gauges with the control level (통제수위) the city already uses.

서울 열린데이터광장 `ListRiverStageService` lists every Seoul river gauge with its live level and four fixed
levels: embankment height (제방고), planned flood level (계획홍수위), riverbed (하상고) and **control level
(통제수위)**. The control level is the existing operational rule for closing riverside paths and roads, so it is
the reference FloodOps' riverside-entrance rule has to be compared with. It is listed on the 민관협력 지원
플랫폼 as «서울시 하천 수위 현황».

    python data/scripts/collect_seoul_river_control_levels.py

Uses SEOUL_OPEN_API_KEY when set. Without it the public `sample` key is used, which only serves rows 1-5
(ERROR-335 beyond that), so the output is partial until a key is issued at data.seoul.go.kr. Output: data/processed/platform/seoul_river_control_levels.csv (fixed levels
plus the reading at collection time) and the raw pages under data/raw/platform/seoul_river_stage/.
"""

from __future__ import annotations

import csv
import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "platform" / "seoul_river_stage"
OUT = ROOT / "data" / "processed" / "platform" / "seoul_river_control_levels.csv"
URL = "http://openapi.seoul.go.kr:8088/{key}/json/ListRiverStageService/{start}/{end}/"
FIELDS = {"WATG_CD": "gauge_code", "WATG_NM": "gauge_name", "RVR_NM": "river", "GU_OFC_NM": "district", "EBM_HGT": "embankment_m",
          "PLAN_FLDE": "planned_flood_m", "RBH": "riverbed_m", "CNTRL_WATL": "control_level_m", "RLTM_RVR_WATL_CNT": "level_at_collection_m",
          "DTRSM_DATA_CLCT_TM": "collected_at"}


def fetch(key: str, start: int, end: int) -> dict:
    with urllib.request.urlopen(URL.format(key=key, start=start, end=end), timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    key = os.environ.get("SEOUL_OPEN_API_KEY", "").strip() or "sample"
    step = 1000 if key != "sample" else 5
    RAW.mkdir(parents=True, exist_ok=True)
    rows, start, total = [], 1, None
    while total is None or start <= total:
        body = fetch(key, start, start + step - 1)["ListRiverStageService"]
        (RAW / f"page_{start:04d}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        total = int(body["list_total_count"])
        rows.extend(body.get("row", []))
        start += step
        if key == "sample":
            break  # the sample key refuses any range beyond rows 1-5
        time.sleep(0.2)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*FIELDS.values(), "has_control_level"])
        writer.writeheader()
        for row in rows:
            item = {name: (str(row.get(src, "")).strip()) for src, name in FIELDS.items()}
            item["has_control_level"] = "true" if float(row.get("CNTRL_WATL") or 0) > 0 else "false"
            writer.writerow(item)
    with_control = sum(1 for r in rows if float(r.get("CNTRL_WATL") or 0) > 0)
    print(f"{len(rows)} gauges of {total}, control level set at {with_control} · key={'own' if key != 'sample' else 'sample'} · {datetime.now():%Y-%m-%d %H:%M}")


if __name__ == "__main__":
    main()

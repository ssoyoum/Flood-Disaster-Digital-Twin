"""Export the 미호강교 flood-season 10-minute water levels used by the closure-criteria review.

Input  : data/processed/hrfco/waterlevel_3011665_10M.csv (collect_hrfco_history.py, gitignored)
Output : data/processed/osong/miho_3011665_10m_floodseason_2019_2026.csv.gz (tracked, shipped to the server image)
         data/manifests/criteria-series.json

Only timestamp and stage height are kept. Values are copied as-is; quality masks are not applied here.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "data" / "processed" / "hrfco" / "waterlevel_3011665_10M.csv"
TARGET = REPO / "data" / "processed" / "osong" / "miho_3011665_10m_floodseason_2019_2026.csv.gz"
MANIFEST = REPO / "data" / "manifests" / "criteria-series.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    raw = SOURCE.read_bytes()
    rows = [r for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))) if r.get("wl")]
    rows.sort(key=lambda r: r["timestamp_kst"])
    body = io.StringIO()
    writer = csv.writer(body, lineterminator="\n")
    writer.writerow(["timestamp_kst", "wl"])
    for row in rows:
        writer.writerow([row["timestamp_kst"], row["wl"]])
    # mtime=0 keeps the archive byte-identical across runs so the manifest hash is reproducible.
    packed = gzip.compress(body.getvalue().encode("utf-8"), mtime=0)
    TARGET.write_bytes(packed)
    years = Counter(r["timestamp_kst"][:4] for r in rows)
    MANIFEST.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "script": "data/scripts/export_criteria_series.py",
        "station_id": "3011665",
        "station": "청주시(미호강교)",
        "interval": "10M",
        "season": "06-01..09-30 each year (collect_hrfco_history.py flood-season window)",
        "source": {"path": str(SOURCE.relative_to(REPO)).replace("\\", "/"), "sha256": sha256(raw), "origin": "HRFCO OpenAPI waterlevel/list/10M"},
        "output": {"path": str(TARGET.relative_to(REPO)).replace("\\", "/"), "sha256": sha256(packed), "rows": len(rows)},
        "rows_by_year": dict(sorted(years.items())),
        "quality": "Values copied without the hourly quality masks (audit_hrfco_quality.py covers 1H only).",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows -> {TARGET.relative_to(REPO)} ({len(packed) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

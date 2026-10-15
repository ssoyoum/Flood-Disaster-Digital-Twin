"""Export the 미호강교 10-minute water levels (all months, 2019-2026) used by the closure-criteria review.

Input  : data/processed/hrfco/waterlevel_3011665_10M.csv (collect_hrfco_history.py, gitignored)
Output : data/processed/osong/miho_3011665_10m_2019_2026.csv.gz (tracked, shipped to the server image)
         data/manifests/criteria-series.json

Only timestamp and stage height are kept. Values are copied as-is: rows with an empty value are left out
(they show up as missing slots) and nothing is smoothed or removed. backend/app/twin.py flags gaps and steps at runtime.
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
TARGET = REPO / "data" / "processed" / "osong" / "miho_3011665_10m_2019_2026.csv.gz"
MANIFEST = REPO / "data" / "manifests" / "criteria-series.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    raw = SOURCE.read_bytes()
    source_rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    rows = [r for r in source_rows if r.get("wl")]
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
        "season": "all months (collect_hrfco_history.py fetch --interval 10M --months 1-12)",
        "source": {"path": str(SOURCE.relative_to(REPO)).replace("\\", "/"), "sha256": sha256(raw), "origin": "HRFCO OpenAPI waterlevel/list/10M"},
        "output": {"path": str(TARGET.relative_to(REPO)).replace("\\", "/"), "sha256": sha256(packed), "rows": len(rows)},
        "source_rows": len(source_rows),
        "source_empty_values": len(source_rows) - len(rows),
        "last_value": rows[-1]["timestamp_kst"] if rows else None,
        "rows_by_year": dict(sorted(years.items())),
        "quality": "Values copied as-is. The criteria review flags missing 10-minute slots and steps >= 0.3 m per 10 minutes at runtime (twin.HISTORY_STEP_REVIEW_M); nothing is removed.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows -> {TARGET.relative_to(REPO)} ({len(packed) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

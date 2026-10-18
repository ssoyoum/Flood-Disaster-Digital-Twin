"""Replay every validation case and store the scorecard the API serves.

    FLOODOPS_TWIN_MODE=replay python data/scripts/build_case_validation.py

Output: data/processed/validation/case_scorecard.json (see backend/app/case_validation.py).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("FLOODOPS_TWIN_MODE", "replay")
from app import case_validation as cv  # noqa: E402


def main() -> None:
    data = cv.build()
    cv.SCORECARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    cv.SCORECARD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for item in data["cases"]:
        print(f"\n{item['title']} · 기준 {item['reference']['at']} {item['reference']['label']}")
        for s in item["signals"]:
            print(f"  {s['signal']:<28} {s['at'] or '—':<17} {s['verdict']}")
        print(f"  기준 시각의 {item['region']} 시설: {item['region_at_reference']}")


if __name__ == "__main__":
    main()

"""Check whether the KMA AWS minute API is open for this key, without printing the key.

    python data/scripts/probe_kma_aws.py

Prints the HTTP status or the number of stations parsed and one sample row. Run it after the API hub 활용신청 is
approved (TODO.md: 기상청 API 허브), then wire backend/app/kma_aws.py into the pluvial rain totals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import kma_aws  # noqa: E402


def main() -> None:
    result = kma_aws.fetch()
    if not result["available"]:
        print("not available:", result["error"])
        return
    rows = result["rows"]
    print(f"{len(rows)} stations at {result['requested_at']}")
    print(json.dumps(next(iter(rows.values())), ensure_ascii=False))


if __name__ == "__main__":
    main()

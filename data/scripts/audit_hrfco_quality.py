"""Audit stored HRFCO hourly water data without changing source observations or fitted models."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.history_quality import audit_hourly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stations", nargs="+", required=True)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data/processed/hrfco")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/processed/hrfco-quality")
    parser.add_argument("--report", type=Path, default=ROOT / "data/manifests/hrfco-quality.json")
    args = parser.parse_args()
    if any(not code.isdigit() for code in args.stations):
        parser.error("station codes must contain only digits")
    policy_path = ROOT / "data/manifests/hrfco-quality-policy.json"
    policy_bytes = policy_path.read_bytes()
    policy = json.loads(policy_bytes)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"policy_id": policy["policy_id"], "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
              "audited_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
              "training_integration_complete": False,
              "station_notes": policy.get("station_notes", {}),
              "source": "stored real HRFCO hourly water observations", "stations": {}}
    for code in dict.fromkeys(args.stations):
        source = args.input_dir / f"waterlevel_{code}_1H.csv"
        if not source.exists():
            report["stations"][code] = {"status": "SOURCE_FILE_UNAVAILABLE"}
            continue
        raw = source.read_bytes()
        rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        audit = audit_hourly(rows, code, policy["quarantines"], policy["jump_review_threshold_m"])
        output = args.output_dir / f"waterlevel_{code}_1H_quality.csv"
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp_kst", "station_id", "wl", "reading_usable", "reading_reasons", "jump_review_required",
                             "training_window_usable", "invalid_input_times", "invalid_target_times", "quarantine_affected"])
            for reading, window in zip(audit["readings"], audit["windows"]):
                writer.writerow([reading["time"], code, reading["water_level_m"], reading["training_reading_usable"],
                                 "|".join(reading["reasons"]), reading["jump_review_required"], window["training_window_usable"],
                                 "|".join(window["invalid_input_times"]), "|".join(window["invalid_target_times"]), window["quarantine_affected"]])
        report["stations"][code] = {key: value for key, value in audit.items() if key not in ("readings", "windows")}
        report["stations"][code].update({"source_file": source.name, "source_sha256": hashlib.sha256(raw).hexdigest(),
                                         "quality_file": output.name, "quality_sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    destination = args.report
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({code: entry.get("counts", entry["status"]) for code, entry in report["stations"].items()}))


if __name__ == "__main__":
    main()

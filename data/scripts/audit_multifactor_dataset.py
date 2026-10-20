"""Audit the generated multi-factor dataset's provenance and missing-data rules.

Run from the repository root:
    python data/scripts/audit_multifactor_dataset.py

This is a dataset release check, not a model-performance or operational-rule test.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/multifactor-dataset.json"
PANEL = "data/processed/multifactor/osong-2023/facility-timeseries-10m.csv.gz"
SENSITIVITY = "data/processed/multifactor/osong-2023/rain-gauge-sensitivity.csv"
LABELS = "data/processed/multifactor/osong-2023/event-labels.csv"
CASE_COVERAGE = "data/processed/multifactor/event-case-coverage.csv"
THRESHOLDS = "data/processed/multifactor/threshold-reference.csv"
STAGES = "data/processed/multifactor/stage-design.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reader(path: Path) -> tuple[TextIO, csv.DictReader]:
    handle: TextIO = gzip.open(path, "rt", encoding="utf-8-sig", newline="") if path.suffix == ".gz" else path.open("r", encoding="utf-8-sig", newline="")
    return handle, csv.DictReader(handle)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def rows(path: Path) -> list[dict[str, str]]:
    handle, csv_reader = reader(path)
    try:
        return list(csv_reader)
    finally:
        handle.close()


def audit() -> dict[str, Any]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("dataset_id") == "floodops-multifactor-v2", "unexpected dataset_id", errors)

    for kind in ("inputs", "outputs"):
        for name, item in (manifest.get(kind) or {}).items() if kind == "inputs" else ((file.get("path", ""), file) for file in manifest.get("outputs", [])):
            rel = item.get("path", "")
            path = ROOT / rel
            require(path.is_file(), f"{kind} missing: {rel}", errors)
            if path.is_file():
                require(sha256(path) == item.get("sha256"), f"{kind} sha256 mismatch: {rel}", errors)

    output_paths = {item.get("path") for item in manifest.get("outputs", [])}
    require(SENSITIVITY in output_paths, "rain-gauge sensitivity output is absent from manifest", errors)

    panel_path = ROOT / PANEL
    panel_handle, panel_reader = reader(panel_path)
    panel_rows = 0
    rain_window_bins = {"rain_1h_mm": (6, "rain_1h_valid_bins"), "rain_3h_mm": (18, "rain_3h_valid_bins"), "rain_12h_mm": (72, "rain_12h_valid_bins")}
    invalid_missing_windows: list[str] = []
    try:
        for row in panel_reader:
            panel_rows += 1
            for amount_key, (expected_bins, valid_key) in rain_window_bins.items():
                amount, valid = row.get(amount_key, ""), row.get(valid_key, "")
                if amount and valid != str(expected_bins):
                    invalid_missing_windows.append(f"{row.get('timestamp_kst')} {amount_key}={amount} valid={valid}")
                    if len(invalid_missing_windows) >= 3:
                        break
            if len(invalid_missing_windows) >= 3:
                break
    finally:
        panel_handle.close()
    expected_panel_rows = manifest.get("osong_panel", {}).get("rows")
    require(panel_rows == expected_panel_rows, f"panel row count mismatch: {panel_rows} != {expected_panel_rows}", errors)
    require(not invalid_missing_windows, "rain windows filled despite incomplete bins: " + "; ".join(invalid_missing_windows), errors)

    labels = rows(ROOT / LABELS)
    event_ids = {row.get("event_id") for row in labels}
    require(len(event_ids) == 1 and "osong-2023" in event_ids, "event labels must remain one Osong incident, not independent cases", errors)
    require(len(labels) == 8, f"unexpected Osong event-label count: {len(labels)}", errors)
    require(all(row.get("source_url") and row.get("source_record") for row in labels), "event label missing source provenance", errors)

    thresholds = rows(ROOT / THRESHOLDS)
    require(all(row.get("source_url") and row.get("source_vintage") and row.get("use_status") for row in thresholds), "threshold row missing provenance/applicability status", errors)
    require(any("SITE_APPLICABILITY_PENDING" in row.get("use_status", "") for row in thresholds), "site-specific control threshold pending state is absent", errors)

    stages = rows(ROOT / STAGES)
    require(len(stages) == 5 and [row.get("stage_order") for row in stages] == ["1", "2", "3", "4", "5"], "five-stage design rows are incomplete or out of order", errors)
    require(all(row.get("validation_status") for row in stages), "stage row missing validation status", errors)

    sensitivity = rows(ROOT / SENSITIVITY)
    require(bool(sensitivity), "rain-gauge sensitivity table is empty", errors)
    for row in sensitivity:
        checkpoint = datetime.strptime(row["checkpoint_at_kst"], "%Y-%m-%d %H:%M")
        latest = datetime.strptime(row["latest_observation_at_or_before_checkpoint_kst"], "%Y-%m-%d %H:%M")
        require(latest <= checkpoint and (checkpoint - latest).total_seconds() < 600,
                f"sensitivity window uses future or stale data: {row.get('station_id')} {row.get('checkpoint_at_kst')}", errors)
        if row.get("series_status") == "NO_SERIES_FILE":
            require(not any(row.get(key) for key in ("rain_10m_mm", "rain_1h_mm", "rain_3h_mm", "rain_12h_mm")),
                    f"missing station series was imputed: {row.get('station_id')} {row.get('checkpoint_at_kst')}", errors)
        if row.get("rain_1h_valid_bins") not in (None, "", "6"):
            require(not row.get("rain_1h_mm"), f"incomplete 1h window has a value: {row.get('station_id')} {row.get('checkpoint_at_kst')}", errors)
        if row.get("rain_3h_valid_bins") not in (None, "", "18"):
            require(not row.get("rain_3h_mm"), f"incomplete 3h window has a value: {row.get('station_id')} {row.get('checkpoint_at_kst')}", errors)
        if row.get("rain_12h_valid_bins") not in (None, "", "72"):
            require(not row.get("rain_12h_mm"), f"incomplete 12h window has a value: {row.get('station_id')} {row.get('checkpoint_at_kst')}", errors)

    case_coverage = rows(ROOT / CASE_COVERAGE)
    confirmed = [row for row in case_coverage if row.get("mechanism_status") == "CONFIRMED_BY_OFFICIAL_INVESTIGATION"]
    require(bool(case_coverage), "event case coverage register is empty", errors)
    require(len(confirmed) == 1 and confirmed[0].get("case_id") == "osong-2023", "unverified case was promoted to confirmed mechanism", errors)
    require(all(row.get("path_calibration_allowed") == "false" for row in case_coverage), "single-event/control-only cases were admitted to path calibration", errors)
    require(all(row.get("reference_source") and row.get("reference_precision") for row in case_coverage), "event case missing source or time precision", errors)

    return {
        "dataset_id": manifest.get("dataset_id"),
        "input_files_checked": len(manifest.get("inputs", {})),
        "output_files_checked": len(manifest.get("outputs", [])),
        "panel_rows_checked": panel_rows,
        "event_labels_checked": len(labels),
        "rain_gauge_sensitivity_rows_checked": len(sensitivity),
        "event_case_coverage_rows_checked": len(case_coverage),
        "threshold_rows_checked": len(thresholds),
        "stage_rows_checked": len(stages),
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }


def main() -> None:
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

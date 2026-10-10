from datetime import datetime, timedelta
import csv
import json
from pathlib import Path
import subprocess
import sys
import pytest
from app.history_quality import audit_hourly

NOW = datetime(2023, 5, 16)
STATION = "3011665"


def series():
    return [{"station_id": STATION, "timestamp_kst": (NOW + timedelta(hours=h)).isoformat(), "wl": str(5 - h / 100)}
            for h in range(60)]


def test_complete_past_and_future_required_and_negative_target_valid():
    result = audit_hourly(series(), STATION)
    windows = result["windows"]
    assert windows[24]["training_window_usable"]
    assert windows[24]["target_maxrise_6h_m"] == -0.01
    assert not windows[23]["training_window_usable"]
    assert not windows[-6]["training_window_usable"]
    assert result["counts"]["usable_training_windows"] == 30


def test_quarantine_propagates_to_both_past_inputs_and_future_target():
    point = (NOW + timedelta(hours=30)).isoformat()
    periods = [{"id": "suspect", "station_id": STATION, "start": point, "end": point, "reason": "pending review"}]
    result = audit_hourly(series(), STATION, periods)
    assert result["readings"][30]["reasons"] == ["RESEARCH_QUARANTINE"]
    assert result["windows"][24]["invalid_target_times"] == [point]
    assert result["windows"][54]["invalid_input_times"] == [point]
    assert result["windows"][24]["target_maxrise_6h_m"] is None
    assert result["windows"][38]["training_window_usable"]


def test_jumps_only_request_review_and_do_not_cross_missing_hours():
    rows = series()
    rows[30]["wl"] = "20"
    result = audit_hourly(rows, STATION)
    assert result["readings"][30]["jump_review_required"]
    assert result["readings"][30]["training_reading_usable"]
    rows.pop(29)
    result = audit_hourly(rows, STATION)
    assert result["readings"][29]["reasons"] == ["MISSING_HOUR"]
    assert not result["readings"][30]["jump_review_required"]
    assert result["gap_intervals"] == [{"start": "2023-05-17T05:00:00", "end": "2023-05-17T05:00:00", "hours": 1}]


def test_recorded_end_is_not_the_last_usable_observation_when_tail_is_empty():
    rows = series()
    rows[-1]["wl"] = ""
    result = audit_hourly(rows, STATION)
    assert result["last"] == rows[-1]["timestamp_kst"]
    assert result["last_usable_observation"] == rows[-2]["timestamp_kst"]


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "", "not-a-number"])
def test_invalid_values_cannot_enter_targets(value):
    rows = series()
    rows[30]["wl"] = value
    result = audit_hourly(rows, STATION)
    assert result["readings"][30]["reasons"] == ["INVALID_VALUE"]
    assert not result["windows"][24]["training_window_usable"]


def test_duplicates_are_rejected_instead_of_choosing_the_last_reading():
    rows = series()
    rows.append({**rows[30], "wl": "99"})
    result = audit_hourly(rows, STATION)
    assert result["readings"][30]["reasons"] == ["DUPLICATE_TIMESTAMP"]
    assert result["readings"][30]["water_level_m"] is None


def test_foreign_station_and_off_grid_times_are_reported_and_empty_data_is_explicit():
    rows = [{"station_id": "other", "timestamp_kst": NOW.isoformat(), "wl": "2"},
            {"station_id": STATION, "timestamp_kst": "2023-05-16T00:10:00", "wl": "2"}]
    result = audit_hourly(rows, STATION)
    assert result["status"] == "NO_HOURLY_RECORDS"
    assert result["counts"] == {"FOREIGN_STATION": 1, "INVALID_HOURLY_TIMESTAMP": 1}


def test_policy_needs_a_reason_and_ordered_times():
    with pytest.raises(ValueError):
        audit_hourly(series(), STATION, [{"id": "bad", "station_id": STATION,
                                        "start": "2023-05-17", "end": "2023-05-16", "reason": "review"}])


def test_cli_preserves_source_and_reports_unavailable_station(tmp_path):
    source = tmp_path / f"waterlevel_{STATION}_1H.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["station_id", "timestamp_kst", "wl"])
        writer.writeheader()
        writer.writerows(series())
    original = source.read_bytes()
    report = tmp_path / "report.json"
    script = Path(__file__).resolve().parents[2] / "data/scripts/audit_hrfco_quality.py"
    result = subprocess.run([sys.executable, str(script), "--stations", STATION, "0000000", "--input-dir", str(tmp_path),
                             "--output-dir", str(tmp_path / "quality"), "--report", str(report)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    summary = json.loads(report.read_text(encoding="utf-8"))
    assert summary["stations"]["0000000"]["status"] == "SOURCE_FILE_UNAVAILABLE"
    assert summary["stations"][STATION]["counts"]["RESEARCH_QUARANTINE"] == 12
    assert len(summary["stations"][STATION]["source_sha256"]) == 64
    assert summary["training_integration_complete"] is False
    assert source.read_bytes() == original


def test_real_miho_episode_quarantines_the_plateau_and_its_next_day_lag():
    root = Path(__file__).resolve().parents[2]
    policy = json.loads((root / "data/manifests/hrfco-quality-policy.json").read_text(encoding="utf-8"))
    with (root / "data/processed/hrfco/waterlevel_3011665_1H.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if "2023-05-15" <= r["timestamp_kst"] < "2023-05-19"]
    result = audit_hourly(rows, STATION, policy["quarantines"])
    assert result["counts"]["RESEARCH_QUARANTINE"] == 12
    assert result["counts"]["quarantine_affected_windows"] == 42
    later = next(w for w in result["windows"] if w["time"] == "2023-05-17T07:00:00")
    assert later["invalid_input_times"] == ["2023-05-16T07:00:00"]
    assert later["target_maxrise_6h_m"] is None

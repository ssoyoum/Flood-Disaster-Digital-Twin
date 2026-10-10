"""Auditable hourly water-level quality masks, independent of any fitted model."""
from collections import Counter
from datetime import datetime, timedelta
import math

INPUT_LAGS_H = (0, 1, 3, 6, 12, 24)
TARGET_LEADS_H = (1, 2, 3, 4, 5, 6)


def audit_hourly(rows, station_id, quarantines=(), jump_m=3.0):
    """Reject invalid/ambiguous readings; abrupt changes request review, not automatic rejection.

    Quarantines are explicit research exclusions, not proof of sensor failure.
    Missing hours are never interpolated. The target requires all six future hours.
    """
    if not math.isfinite(jump_m) or jump_m <= 0:
        raise ValueError("jump_m must be positive and finite")
    periods = []
    for period in quarantines:
        if period["station_id"] != station_id:
            continue
        start, end = datetime.fromisoformat(period["start"]), datetime.fromisoformat(period["end"])
        if start > end or not period.get("reason"):
            raise ValueError("quarantine needs an ordered interval and a reason")
        periods.append((start, end, period["id"]))
    grouped, row_issues = {}, Counter()
    for row in rows:
        if str(row.get("station_id")) != station_id:
            row_issues["FOREIGN_STATION"] += 1
            continue
        try:
            stamp = datetime.fromisoformat(row["timestamp_kst"])
            if stamp.tzinfo is not None or stamp.minute or stamp.second or stamp.microsecond:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            row_issues["INVALID_HOURLY_TIMESTAMP"] += 1
            continue
        try:
            value = float(row["wl"])
            if not math.isfinite(value):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            value = None
        grouped.setdefault(stamp, []).append(value)
    if not grouped:
        return {"station_id": station_id, "status": "NO_HOURLY_RECORDS", "counts": dict(row_issues),
                "readings": [], "windows": [], "jump_review": []}
    first, last = min(grouped), max(grouped)
    reasons, values, readings, jumps, gaps = {}, {}, [], [], []
    stamp = first
    previous = None
    while stamp <= last:
        samples = grouped.get(stamp, [])
        bad = []
        if not samples:
            bad.append("MISSING_HOUR")
            if not readings or "MISSING_HOUR" not in readings[-1]["reasons"]:
                gaps.append({"start": stamp.isoformat(), "end": stamp.isoformat(), "hours": 0})
            gaps[-1]["end"] = stamp.isoformat()
            gaps[-1]["hours"] += 1
        elif len(samples) > 1:
            bad.append("DUPLICATE_TIMESTAMP")
        elif samples[0] is None:
            bad.append("INVALID_VALUE")
        quarantine_ids = [pid for start, end, pid in periods if start <= stamp <= end]
        if quarantine_ids:
            bad.append("RESEARCH_QUARANTINE")
        value = samples[0] if len(samples) == 1 else None
        values[stamp] = value
        reasons[stamp] = bad
        review = bool(value is not None and previous is not None and abs(value - previous) >= jump_m)
        if review:
            jumps.append({"time": stamp.isoformat(), "previous_time": (stamp - timedelta(hours=1)).isoformat(),
                          "change_m": round(value - previous, 6), "status": "REVIEW_REQUIRED"})
        readings.append({"time": stamp.isoformat(), "water_level_m": value,
                         "training_reading_usable": not bad, "reasons": bad,
                         "quarantine_ids": quarantine_ids, "jump_review_required": review})
        previous = value
        stamp += timedelta(hours=1)
    windows = []
    for reading in readings:
        anchor = datetime.fromisoformat(reading["time"])
        past = [anchor - timedelta(hours=h) for h in INPUT_LAGS_H]
        future = [anchor + timedelta(hours=h) for h in TARGET_LEADS_H]
        input_bad = [t.isoformat() for t in past if t not in reasons or reasons[t]]
        target_bad = [t.isoformat() for t in future if t not in reasons or reasons[t]]
        quarantine_affected = any("RESEARCH_QUARANTINE" in reasons.get(t, []) for t in past + future)
        usable = not input_bad and not target_bad
        target = round(max(values[t] for t in future) - values[anchor], 6) if usable else None
        windows.append({"time": reading["time"], "training_window_usable": usable,
                        "invalid_input_times": input_bad, "invalid_target_times": target_bad,
                        "quarantine_affected": quarantine_affected, "target_maxrise_6h_m": target})
    counts = Counter(reason for reading in readings for reason in reading["reasons"])
    counts.update(row_issues)
    counts.update({"hourly_slots": len(readings), "unique_recorded_hours": len(grouped),
                   "usable_readings": sum(r["training_reading_usable"] for r in readings),
                   "usable_training_windows": sum(w["training_window_usable"] for w in windows),
                   "quarantine_affected_windows": sum(w["quarantine_affected"] for w in windows),
                   "jump_review_count": len(jumps)})
    usable_times = [r["time"] for r in readings if r["training_reading_usable"]]
    return {"station_id": station_id, "status": "AUDITED", "counts": dict(counts),
            "first": first.isoformat(), "last": last.isoformat(), "readings": readings,
            "first_usable_observation": usable_times[0] if usable_times else None,
            "last_usable_observation": usable_times[-1] if usable_times else None,
            "gap_intervals": gaps, "windows": windows, "jump_review": jumps}

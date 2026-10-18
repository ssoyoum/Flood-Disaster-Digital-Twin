"""Local, append-only operator confirmation records for operational facilities."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCK = threading.Lock()


class DecisionRecordCreate(BaseModel):
    checked_by: str = Field(min_length=1, max_length=80)
    confirmation: Literal["CONFIRMED", "NO_ACTION", "ESCALATE"]
    acknowledged: Literal[True]
    note: str = Field(default="", max_length=500)

    @field_validator("checked_by")
    @classmethod
    def checked_by_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("checked_by must contain a name or role")
        return value

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        return value.strip()


def _path() -> Path:
    configured = os.environ.get("FLOODOPS_DECISION_LOG_PATH")
    return Path(configured).expanduser() if configured else REPO_ROOT / "data" / "local" / "operational-decisions.jsonl"


def list_records(facility_id: str, limit: int = 20) -> list[dict[str, Any]]:
    path = _path()
    if not path.is_file():
        return []
    with _LOCK:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
    records = []
    for line in lines:
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if record.get("facility_id") == facility_id:
            records.append(record)
    return sorted(records, key=lambda row: row.get("recorded_at", ""), reverse=True)[:limit]


def append_record(
    facility: dict[str, Any],
    status: dict[str, Any],
    request: DecisionRecordCreate,
) -> dict[str, Any]:
    observation = status.get("observation")
    if not observation:
        raise ValueError("An observation is required before a confirmation can be recorded")

    rule = status.get("rule") or facility["control_rule"]
    levels = status.get("levels_m") or facility["gauge"]["levels_m"]
    stage_floor = rule.get("stage_floor")
    record = {
        "record_id": uuid.uuid4().hex,
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "facility_id": facility["id"],
        "facility_name": facility["name"],
        "source_mode": status.get("mode", "unknown"),
        "observation_at": observation.get("time"),
        "gauge_station": observation.get("station"),
        "water_level_m": observation.get("water_level_m"),
        "stage": status.get("stage"),
        "stage_label": status.get("stage_label"),
        "recommendation": status.get("recommendation"),
        "recommendation_reason": status.get("reason"),
        "criteria": {
            "rule_id": rule.get("id"),
            "stage_floor": stage_floor,
            "stage_floor_level_m": levels.get(stage_floor) if stage_floor else None,
            "planned_flood_level_m": levels.get("planned_flood"),
            "lead_threshold_min": rule.get("lead_threshold_min"),
            "minutes_to_planned_flood": status.get("minutes_to_planned_flood"),
        },
        "confirmation": request.confirmation,
        "acknowledged": request.acknowledged,
        "checked_by": request.checked_by,
        "note": request.note,
    }

    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    with _LOCK:
        with path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()
    return record

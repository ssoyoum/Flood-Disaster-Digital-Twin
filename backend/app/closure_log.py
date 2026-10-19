"""Local, append-only closure records: when an operator actually closed (or chose not to close) a facility.

The confirmation log (decision_log) says an operator saw a recommendation. This log says what they did and
when, which is what the post-season scorecard compares the rule against. Records are never rewritten: a later
reopening time is appended as an amendment line and merged on read, so the original entry stays auditable.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
_LOCK = threading.Lock()
# A record may be typed a little ahead of the clock on a slow terminal, not hours ahead.
FUTURE_TOLERANCE = timedelta(minutes=10)

Kind = Literal["CLOSED", "NOT_CLOSED"]
Trigger = Literal["RECOMMENDATION", "OFFICIAL_FORECAST", "FIELD", "ORDER", "OTHER"]


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    # Times are entered and stored in KST wall time like the rest of the twin.
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


class ClosureRecordCreate(BaseModel):
    kind: Kind
    started_at: str = Field(description="CLOSED: when entry was blocked. NOT_CLOSED: when the operator decided not to close.")
    ended_at: str | None = Field(default=None, description="CLOSED only: when the facility reopened, if known")
    trigger: Trigger = "RECOMMENDATION"
    checked_by: str = Field(min_length=1, max_length=80)
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

    @field_validator("started_at", "ended_at")
    @classmethod
    def must_be_iso(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        return _parse(value).isoformat(timespec="minutes")

    @model_validator(mode="after")
    def times_must_be_consistent(self) -> "ClosureRecordCreate":
        start = _parse(self.started_at)
        if start > datetime.now() + FUTURE_TOLERANCE:
            raise ValueError("started_at is in the future")
        if self.kind == "NOT_CLOSED" and self.ended_at:
            raise ValueError("a NOT_CLOSED record has no reopening time")
        if self.ended_at and _parse(self.ended_at) <= start:
            raise ValueError("ended_at must be after started_at")
        return self


class ClosureRecordEnd(BaseModel):
    ended_at: str
    checked_by: str = Field(min_length=1, max_length=80)
    note: str = Field(default="", max_length=500)

    @field_validator("ended_at")
    @classmethod
    def must_be_iso(cls, value: str) -> str:
        return _parse(value).isoformat(timespec="minutes")


def _path() -> Path:
    configured = os.environ.get("FLOODOPS_CLOSURE_LOG_PATH")
    return Path(configured).expanduser() if configured else REPO_ROOT / "data" / "local" / "closure-records.jsonl"


def _append(entry: dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    with _LOCK:
        with path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()


def _lines() -> list[dict[str, Any]]:
    path = _path()
    if not path.is_file():
        return []
    with _LOCK:
        try:
            raw = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
    rows = []
    for line in raw:
        try:
            rows.append(json.loads(line))
        except (json.JSONDecodeError, TypeError):
            continue
    return rows


def list_records(facility_id: str, season: int | None = None) -> list[dict[str, Any]]:
    """Records for one facility with their amendments applied, oldest first."""

    records: dict[str, dict[str, Any]] = {}
    for row in _lines():
        if row.get("facility_id") != facility_id:
            continue
        if row.get("type") == "amendment":
            target = records.get(row.get("record_id"))
            if target is not None:
                target["ended_at"] = row["ended_at"]
                target.setdefault("amendments", []).append({key: row.get(key) for key in ("recorded_at", "checked_by", "ended_at", "note")})
        else:
            records[row["record_id"]] = dict(row)
    rows = sorted(records.values(), key=lambda r: r["started_at"])
    if season is not None:
        rows = [r for r in rows if r["started_at"].startswith(str(season))]
    return rows


def append_record(facility: dict[str, Any], request: ClosureRecordCreate) -> dict[str, Any]:
    record = {
        "type": "record",
        "record_id": uuid.uuid4().hex,
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "facility_id": facility["id"],
        "facility_name": facility["name"],
        "kind": request.kind,
        "started_at": request.started_at,
        "ended_at": request.ended_at,
        "trigger": request.trigger,
        "checked_by": request.checked_by,
        "note": request.note,
        "rule_snapshot": facility.get("control_rule"),
    }
    _append(record)
    return record


def end_record(facility: dict[str, Any], record_id: str, request: ClosureRecordEnd) -> dict[str, Any]:
    current = next((r for r in list_records(facility["id"]) if r["record_id"] == record_id), None)
    if current is None:
        raise LookupError(f"Unknown closure record: {record_id}")
    if current["kind"] != "CLOSED":
        raise ValueError("only a CLOSED record can be given a reopening time")
    if _parse(request.ended_at) <= _parse(current["started_at"]):
        raise ValueError("ended_at must be after started_at")
    _append({
        "type": "amendment",
        "record_id": record_id,
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "facility_id": facility["id"],
        "ended_at": request.ended_at,
        "checked_by": request.checked_by.strip(),
        "note": request.note.strip(),
    })
    return next(r for r in list_records(facility["id"]) if r["record_id"] == record_id)

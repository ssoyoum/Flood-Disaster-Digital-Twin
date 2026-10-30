"""Closure records and the season scorecard that matches them with the rule's recommendations."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FACILITY = "gungpyeong2-underpass"
BASE = f"/api/twin/facilities/{FACILITY}"


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOODOPS_CLOSURE_LOG_PATH", str(tmp_path / "closures.jsonl"))


def closed(started_at, **extra):
    return {"kind": "CLOSED", "started_at": started_at, "checked_by": "당직 담당자", **extra}


def test_records_are_listed_by_season():
    assert client.post(f"{BASE}/closures", json=closed("2023-07-15T07:00")).status_code == 200
    assert len(client.get(f"{BASE}/closures?season=2023").json()["records"]) == 1
    assert client.get(f"{BASE}/closures?season=2022").json()["records"] == []


@pytest.mark.parametrize("body", [
    {"kind": "NOT_CLOSED", "started_at": "2023-07-15T07:00", "ended_at": "2023-07-15T09:00", "checked_by": "a"},
    closed("2023-07-15T07:00", ended_at="2023-07-15T06:00"),
    closed("2099-01-01T00:00"),
    closed("2023-07-15T07:00", checked_by="   "),
])
def test_inconsistent_records_are_rejected(body):
    assert client.post(f"{BASE}/closures", json=body).status_code == 422


def test_reopening_is_an_amendment_not_a_rewrite():
    record = client.post(f"{BASE}/closures", json=closed("2023-07-15T07:00")).json()
    ended = client.patch(f"{BASE}/closures/{record['record_id']}", json={"ended_at": "2023-07-15T18:00", "checked_by": "야간 담당자"}).json()
    assert ended["ended_at"] == "2023-07-15T18:00"
    assert ended["amendments"][0]["checked_by"] == "야간 담당자"
    assert ended["checked_by"] == "당직 담당자"
    declined = client.post(f"{BASE}/closures", json={"kind": "NOT_CLOSED", "started_at": "2023-07-15T06:00", "checked_by": "a"}).json()
    assert client.patch(f"{BASE}/closures/{declined['record_id']}", json={"ended_at": "2023-07-15T18:00", "checked_by": "a"}).status_code == 422
    assert client.patch(f"{BASE}/closures/nope", json={"ended_at": "2023-07-15T18:00", "checked_by": "a"}).status_code == 404


def test_season_without_records_leaves_the_recommendation_unrecorded():
    card = client.get(f"{BASE}/season-scorecard?season=2023").json()
    assert card["counts"]["unrecorded"] == 1 and card["counts"]["hit"] == 0
    assert card["rows"][0]["episode"]["start"] == "2023-07-15T05:50:00"
    assert sum(c["is_current_rule"] for c in card["candidates"]) == 1 and len(card["candidates"]) == 12


def test_season_matches_closures_to_recommendations():
    client.post(f"{BASE}/closures", json=closed("2023-07-15T07:00"))
    client.post(f"{BASE}/closures", json=closed("2023-08-20T10:00", trigger="FIELD"))
    card = client.get(f"{BASE}/season-scorecard?season=2023").json()
    assert card["counts"]["hit"] == 1 and card["counts"]["miss"] == 1
    hit = next(row for row in card["rows"] if row["outcome"] == "hit")
    assert hit["lead_min"] == 70  # recommendation 05:50, closure 07:00


def test_operator_decision_not_to_close_is_kept_apart_from_no_record():
    client.post(f"{BASE}/closures", json={"kind": "NOT_CLOSED", "started_at": "2023-07-15T06:10", "checked_by": "a", "note": "현장 수위 낮음"})
    card = client.get(f"{BASE}/season-scorecard?season=2023").json()
    assert card["counts"]["not_closed"] == 1 and card["counts"]["unrecorded"] == 0

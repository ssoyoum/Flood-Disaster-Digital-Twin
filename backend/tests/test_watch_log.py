import json

from app import watch_log


def _write(tmp_path, lines):
    (tmp_path / "2026.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")


def test_consecutive_snapshots_form_one_episode_and_gaps_split(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOODOPS_WATCH_LOG_DIR", str(tmp_path))
    fid = "gungpyeong2-underpass"
    _write(tmp_path, [
        {"at": "2026-07-10T06:00:00", "total": 900, "facilities": {fid: [2, 0]}},
        {"at": "2026-07-10T06:10:00", "total": 900, "facilities": {fid: [3, 1]}},
        {"at": "2026-07-10T06:20:00", "total": 900, "facilities": {}},
        {"at": "2026-07-10T08:00:00", "total": 900, "facilities": {fid: [2, 0]}},
    ])
    board = watch_log.season_board(2026)
    row = next(r for r in board["facilities"] if r["facility_id"] == fid)
    assert row["episodes"] == 2 and row["episodes_with_official"] == 1 and row["episodes_alone"] == 1
    assert row["peak_label"] == "경계" and row["minutes_by_level"]["주의"] == 20 and row["minutes_by_level"]["경계"] == 10
    assert board["coverage"]["snapshots"] == 4 and board["coverage"]["from"] == "2026-07-10T06:00:00"
    assert board["counts"]["reached"]["경계"] == 1


def test_no_record_yet_is_an_empty_board_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOODOPS_WATCH_LOG_DIR", str(tmp_path))
    board = watch_log.season_board(2026)
    assert board["coverage"]["snapshots"] == 0 and board["facilities"] == []


def test_only_live_snapshots_are_written(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOODOPS_WATCH_LOG_DIR", str(tmp_path))
    from app import facility_risk

    monkeypatch.setattr(facility_risk, "facility_risk", lambda **_: {"mode": "replay", "at": "2026-07-10T06:00:00", "counts": {"total": 1}, "facilities": []})
    assert watch_log.record_once() is None and not list(tmp_path.iterdir())
    monkeypatch.setattr(facility_risk, "facility_risk", lambda **_: {
        "mode": "live", "at": "2026-07-10T06:00:00", "observed_at": None, "rain_at": None, "counts": {"total": 2},
        "facilities": [{"facility_id": "a", "level": 0, "official": None}, {"facility_id": "b", "level": 2, "official": {"level": "advisory"}}]})
    line = watch_log.record_once()
    assert line["facilities"] == {"b": [2, 1]}
    assert (tmp_path / "2026.jsonl").read_text(encoding="utf-8").count("\n") == 1

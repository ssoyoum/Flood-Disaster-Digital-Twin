"""Official flood forecast issuances replayed from the collected history."""

from app import flood_forecast as ff


def test_osong_warning_is_active_on_the_morning_of_the_flood():
    active = ff.active_at("2023-07-15T06:00:00")
    miho = active["3011665"]
    assert miho["level"] == "warning" and miho["issued_at"] == "2023-07-15T04:10" and miho["minutes_since_issue"] == 110
    assert active["3011645"]["level"] == "warning"  # 흥덕교 03:00


def test_issuance_is_inactive_before_it_and_after_its_release():
    assert "3011665" not in ff.active_at("2023-07-14T12:00:00")
    assert ff.active_at("2023-07-14T18:00:00")["3011665"]["level"] == "advisory"  # 17:20 홍수주의보
    assert "3011665" not in ff.active_at("2023-07-17T12:00:00")  # 09:50 해제


def test_mannyeon_2020_warning_was_issued_below_the_warning_level():
    miho = ff.active_at("2020-07-30T08:00:00")["3009670"]
    assert miho["level"] == "warning" and miho["level_at_issue_m"] == 4.17 and miho["forecast_level_m"] == 4.5


def test_level_of_reads_issue_kinds():
    assert ff.level_of("홍수경보 변경발령") == "warning"
    assert ff.level_of("홍수주의보 발령") == "advisory"
    assert ff.level_of("홍수경보 해제") is None


def test_replay_summary_lists_warnings_first():
    data = ff.summary("2023-07-15T06:00:00")
    assert data["mode"] == "replay" and data["counts"]["warning"] >= 2
    levels = [row["level"] for row in data["active"]]
    assert levels == sorted(levels, key=lambda level: level != "warning")

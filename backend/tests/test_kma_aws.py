"""KMA AWS minute parser: column order comes from the header, missing values become None."""

import pytest

from app import kma_aws

BODY = """#START7777
# YYMMDDHHMI STN WD1 WS1 RN-15m RN-60m RN-12H RN-DAY TA
202307150600 131 270 3.1 12.5 40.0 180.5 190.0 22.1
202307150600 133 180 1.0 -99.0 -99.0 0.0 0.0 23.4
#7777END
"""


def test_parse_reads_rain_columns_by_header_name():
    rows = kma_aws.parse(BODY)
    assert rows["131"] == {"stn": "131", "time": "2023-07-15T06:00", "rain_15m_mm": 12.5, "rain_1h_mm": 40.0, "rain_12h_mm": 180.5, "rain_day_mm": 190.0}
    assert rows["133"]["rain_1h_mm"] is None and rows["133"]["rain_12h_mm"] == 0.0


def test_parse_follows_a_different_column_order():
    body = "# STN YYMMDDHHMI RN-60m\n131 202307150600 7.5\n"
    assert kma_aws.parse(body)["131"]["rain_1h_mm"] == 7.5


def test_parse_rejects_a_body_without_the_header():
    with pytest.raises(ValueError):
        kma_aws.parse("<html>403 Forbidden</html>")


def test_fetch_without_a_key_reports_not_configured(monkeypatch):
    monkeypatch.setattr("app.llm_planner._load_env_file_once", lambda: None)
    monkeypatch.delenv("KMA_API_HUB_KEY", raising=False)
    assert kma_aws.fetch() == {"available": False, "error": "KMA_API_HUB_KEY is not configured", "rows": {}}

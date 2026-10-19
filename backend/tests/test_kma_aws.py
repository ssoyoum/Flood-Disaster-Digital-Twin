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


STATIONS = """# STN LON LAT STN_SP HT HT_WD LAU STN STN_KO STN_EN FCT_ID LAW_ID BASIN LAW_ADDR
   42  126.59737000   35.93681000 01211111      2.05     10.00    0 146 군산오식도           ----                 21F10501 5213014700 ---- 전북특별자치도 군산시 오식도동
   92  128.66298000   38.05903000 20111000     75.40     10.00 4113 113 양양(공)             ----                 11D20403 5183032021  221 강원특별자치도 양양군 손양면 동호리
"""


def test_parse_stations_reads_position_name_and_address():
    rows = kma_aws.parse_stations(STATIONS)
    assert rows["42"] == {"stn": "42", "name": "군산오식도", "lon": 126.59737, "lat": 35.93681, "address": "전북특별자치도 군산시 오식도동"}
    assert rows["92"]["name"] == "양양(공)" and rows["92"]["address"].startswith("강원특별자치도 양양군")


def test_live_rain_adds_kma_stations_and_survives_an_outage(monkeypatch):
    from app import facility_risk as fr

    monkeypatch.setattr(kma_aws, "stations", lambda: {"42": {"stn": "42", "name": "군산오식도", "lon": 126.6, "lat": 35.94, "address": "전북특별자치도 군산시"}})
    monkeypatch.setattr(kma_aws, "rain_totals", lambda: {"rows": {"kma:42": {"rain_10m_mm": None, "rain_1h_mm": 20.0, "rain_3h_mm": 65.0, "rain_12h_mm": 70.0}},
                                                         "observed_at": None, "error": None})
    _, totals, basis = fr._with_kma(None, {}, "base")
    assert totals["kma:42"]["rain_3h_mm"] == 65.0 and "기상청 AWS" in basis
    assert fr._gauge("kma:42").name == "군산오식도(기상청 AWS)" and fr._nearest_rain_codes(126.61, 35.94, set(totals))[0][0] == "kma:42"
    assert fr._pluvial_level({**totals["kma:42"]})[0] == 2
    monkeypatch.setattr(kma_aws, "rain_totals", lambda: (_ for _ in ()).throw(OSError("down")))
    assert fr._with_kma(None, {"x": {}}, "base") == (None, {"x": {}}, "base")


def test_fetch_without_a_key_reports_not_configured(monkeypatch):
    monkeypatch.setattr("app.llm_planner._load_env_file_once", lambda: None)
    monkeypatch.delenv("KMA_API_HUB_KEY", raising=False)
    assert kma_aws.fetch() == {"available": False, "error": "KMA_API_HUB_KEY is not configured", "rows": {}}

from app import kma_weather_warning as w

# Shape of a real wrn_now_data.php response (tm=202007232130): dash-padded header, comma rows ending in "=".
BODY = """#START7777
#---------------------------------------------------------------------------------------------------
#  특보현황 조회
#---------------------------------------------------------------------------------------------------
# REG_UP  REG_UP_KO-------------------------------  REG_ID    REG_KO----------------------------------  TM_FC         TM_EF         WRN     LVL       CMD   ED_TM
L1150000, 부산광역시                              , L1080100, 부산광역시                              , 202007232000, 202007232000, 호우  , 경보    , 변경,  ,=
L1020000, 강원도                                  , L1025020, 강원북부산지                            , 202007231600, 202007240559, 호우  , 예비    , 발표,  ,=
L1100000, 경상남도                                , L1100100, 창원시                                  , 202007231900, 202007231900, 호우  , 주의    , 발표,  ,=
L1100000, 경상남도                                , L1100200, 김해시                                  , 202007231700, 202007231700, 호우  , 주의    , 해제,  ,=
S1311000, 남해동부앞바다                          , S1311100, 부산앞바다                              , 202007232100, 202007240000, 풍랑  , 주의    , 발표, 25일 새벽(03시~06시),=
#7777END
"""


def test_parse_reads_dash_padded_header_and_comma_rows():
    rows = w.parse(BODY)
    assert [(r["area"], r["level"], r["command"]) for r in rows] == [("부산광역시", "warning", "변경"), ("창원시", "advisory", "발표")]
    busan = rows[0]
    assert busan["province"] == "부산광역시"
    assert busan["region_code"] == "L1080100"
    assert busan["issued_at"] == "2020-07-23T20:00"
    assert busan["effective_at"] == "2020-07-23T20:00"


def test_parse_skips_preliminary_lifted_and_non_rain_rows():
    areas = {r["area"] for r in w.parse(BODY)}
    assert "강원북부산지" not in areas  # 예비특보 is not in effect
    assert "김해시" not in areas  # 해제
    assert "부산앞바다" not in areas  # 풍랑


def test_at_keeps_announced_command_as_not_in_effect(monkeypatch):
    from datetime import datetime

    body = BODY.replace("202007232000, 202007232000, 호우  , 경보", "202007232000, 202007232100, 호우  , 경보")
    monkeypatch.setenv("KMA_API_HUB_KEY", "test-key")
    monkeypatch.setattr(w, "_request", lambda key, tm="": w.parse(body))
    rows = {r["area"]: r for r in w.at(datetime(2020, 7, 23, 20, 30))["rows"]}
    assert rows["부산광역시"]["in_effect"] is False
    assert rows["창원시"]["in_effect"] is True


def test_parse_still_reads_whitespace_rows():
    body = "# REG_UP REG_UP_KO REG_ID REG_KO TM_FC TM_EF WRN LVL CMD\nL1 충청북도 L2 청주시 202307150410 202307150410 R 2 발표\n"
    assert [(r["area"], r["level"]) for r in w.parse(body)] == [("청주시", "warning")]

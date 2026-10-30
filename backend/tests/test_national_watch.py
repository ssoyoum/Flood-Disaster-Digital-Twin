"""National watch over the stored hourly series (replay) and the board-operator Agent tools."""

from dataclasses import replace
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from app import agent_runner, agent_watch, national_watch as nw
from app.main import app

client = TestClient(app)
AT = "2023-07-15T06:00:00"


@pytest.fixture(autouse=True)
def replay(monkeypatch):
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")


def test_catalogue_classifies_each_station_against_its_own_levels():
    station = nw.stations()["3011665"]
    assert station.region == "충북" and station.short_name == "미호강교"
    assert station.levels_m["warning"] == 8.0 and station.levels_m["planned_flood"] == 9.38
    assert nw.classify_stage(8.91, station.levels_m) == "warning"
    assert nw.classify_stage(1.0, {}) == "unrated"


def test_replay_overview_counts_stages_and_links_facilities_by_tier():
    data = nw.overview(at=AT)
    assert data["mode"] == "replay" and data["stations_total"] == len(nw.stored_station_codes())
    assert data["counts"]["by_stage"]["warning"] >= 1 and data["counts"]["by_stage"]["planned_flood"] >= 1
    miho = next(row for row in data["stations"] if row["code"] == "3011665")
    assert miho["stage"] == "warning" and miho["observation"]["water_level_m"] == 8.91
    tiers = {f["tier"] for f in miho["facilities"]}
    assert "operational" in tiers and "watch" in tiers
    assert data["counts"]["facilities_operational"] == 1
    assert data["stations"][0]["stage"] == "planned_flood"  # priority order: stage first


def test_overview_region_filter_uses_station_regions(monkeypatch):
    # The committed replay stations can all belong to Chungbuk. Give one stored
    # station a second region so a filter regression is detectable in any checkout.
    catalogue = dict(nw.stations())
    other = next(code for code in nw.stored_station_codes() if code != "3011665")
    catalogue[other] = replace(catalogue[other], region="서울")
    monkeypatch.setattr(nw, "stations", lambda: catalogue)
    region = nw.overview(at=AT, region="충북")
    assert region["stations_total"] == nw.overview(at=AT)["stations_total"] - 1
    assert all(row["region"] == "충북" for row in region["stations"])


def test_changes_between_hours_uses_each_stations_thresholds(monkeypatch):
    now = datetime.fromisoformat(AT)
    before = now - timedelta(hours=1)
    station = nw.stations()["3011665"]
    # Both levels use the station's registered 8.0 m warning threshold; no raw
    # archive update can silently change this test from a stage move to a rise.
    current = nw.Snapshot(now, "1H", {station.code: (now, 8.5)})
    earlier = nw.Snapshot(before, "1H", {station.code: (before, 7.5)})
    monkeypatch.setattr(nw, "stations", lambda: {station.code: station})
    monkeypatch.setattr(nw, "_frame", lambda at: ("replay", now, current, {}, [], None))
    monkeypatch.setattr(nw, "replay_snapshot", lambda at: (earlier, {}))
    diff = nw.changes(60, at=AT)
    assert diff["available"]
    assert [(item["code"], item["from"], item["to"], item["delta_m"]) for item in diff["stage_up"]] == [
        (station.code, "advisory", "warning", 1.0)
    ]
    assert diff["stage_down"] == [] and diff["new_rising"] == []


def test_station_detail_rate_and_recent_series():
    detail = nw.station_detail("3011665", at=AT)
    assert detail["rate_m_per_10min"] > 0 and detail["minutes_to_planned_flood"] is not None
    assert detail["recent"][-1]["water_level_m"] == 8.91 and len(detail["recent"]) >= 20
    with pytest.raises(KeyError):
        nw.station_detail("0000000", at=AT)


def test_watch_api_routes():
    assert client.get("/api/watch/overview", params={"at": AT, "region": "충청북도", "limit": 3}).json()["filter"]["region"] == "충북"
    assert client.get("/api/watch/stations/3011665", params={"at": AT}).json()["stage"] == "warning"
    assert client.get("/api/watch/stations/0000000").status_code == 404
    assert client.get("/api/watch/changes", params={"at": AT, "since_min": 60}).json()["available"]
    facilities = client.get("/api/watch/facilities").json()
    assert any(f["tier"] == "operational" for f in facilities) and len(facilities) >= 200
    assert [t["name"] for t in client.get("/api/agent/tools", params={"board": "watch"}).json()] == sorted(agent_watch.TOOL_NAMES, key=[t["name"] for t in agent_watch.tools()].index)


@pytest.mark.parametrize("question,tool,key", [
    ("충북 보여줘", "navigate_board", "region"),
    ("미호강교 지금 몇 단계야?", "get_station_status", "station"),
    ("지금 가장 위험한 곳 5곳 알려줘", "rank_priority", "limit"),
    ("지난 1시간 동안 뭐가 바뀌었어?", "summarize_changes", "since_min"),
    ("지금 상황 보고 초안 써줘", "draft_situation_report", None),
    ("궁평2지하차도 규칙 성적표 보여줘", "rule_scorecard", "facility"),
    ("경보 이상인 곳만 보여줘", "get_watch_overview", "min_stage"),
])
def test_hints_pick_the_board_tool_and_carry_only_the_users_words(question, tool, key):
    hint = agent_watch.hints(question)[0]
    assert hint["tool_name"] == tool
    if key:
        assert key in hint["parameters"]
    clean = agent_watch.validate(tool, hint["parameters"], question)
    if key:
        assert key in clean


def test_validate_rejects_values_the_user_did_not_write():
    with pytest.raises(ValueError):
        agent_watch.validate("navigate_board", {"region": "강원"}, "충북 보여줘")
    with pytest.raises(ValueError):
        agent_watch.validate("rank_priority", {"limit": 9}, "가장 위험한 곳 5곳")
    with pytest.raises(ValueError):
        agent_watch.validate("get_station_status", {"station": "미호강교"}, "지금 몇 단계야?")


def test_board_scope_answers_without_a_model_and_returns_a_view(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: (_ for _ in ()).throw(agent_runner.LlmPlannerUnavailable("offline")))
    body = client.post("/api/agent/ask", json={"board": "watch", "message": "미호강교 지금 몇 단계야?", "observation_at": AT}).json()
    assert body["status"] == "ANSWERED" and body["tool_calls"][0]["tool_name"] == "get_station_status"
    view = body["tool_calls"][0]["result"]["view"]
    assert view["station_code"] == "3011665" and view["center"]
    assert "8.91" in body["answer"] and agent_watch.WATCH_CAVEAT in body["answer"] and "예보가 아닙니다" in body["answer"]
    moved = client.post("/api/agent/ask", json={"board": "watch", "message": "강원도로 가자", "observation_at": AT}).json()
    assert moved["tool_calls"][0]["result"]["view"]["region"] == "강원"


def test_board_scope_scorecard_and_refusals(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: (_ for _ in ()).throw(agent_runner.LlmPlannerUnavailable("offline")))
    card = client.post("/api/agent/ask", json={"board": "watch", "message": "궁평2지하차도 규칙 성적표 보여줘", "observation_at": AT}).json()
    score = card["tool_calls"][0]["result"]["scorecard"]
    assert score["hit"] == 1 and score["false_alarm_candidates"] == 0 and 2025 in score["close_call_years"]
    assert "오경보로 확정하지 않습니다" in card["answer"]
    forecast = client.post("/api/agent/ask", json={"board": "watch", "message": "내일 홍수 날까?", "observation_at": AT}).json()
    assert forecast["status"] == "NEEDS_DATA" and not forecast["tool_calls"]
    assert client.post("/api/agent/ask", json={"board": "watch", "facility_id": "gungpyeong2-underpass", "message": "x"}).status_code == 422


def test_model_answer_claiming_safety_is_replaced_by_the_tool_summary(monkeypatch):
    actions = iter([
        agent_runner.AgentAction(action="tool", tool_name="get_station_status", parameters={"station": "미호강교"}),
        agent_runner.AgentAction(action="final", answer="미호강교는 8.91 m이고 지금은 안전합니다 [1].", evidence_calls=[1]),
    ])
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: next(actions))
    body = client.post("/api/agent/ask", json={"board": "watch", "message": "미호강교 지금 몇 단계야?", "observation_at": AT}).json()
    assert body["diagnostics"]["completion_source"] == "registered_tools" and "안전합니다" not in body["answer"]


def test_rain_classes_follow_kma_intensity_bins():
    assert nw.rain_class(0) == ("none", "강우 없음") and nw.rain_class(None)[0] == "none"
    assert nw.rain_class(2.9)[0] == "light" and nw.rain_class(3)[0] == "moderate"
    assert nw.rain_class(15)[0] == "heavy" and nw.rain_class(30)[0] == "very_heavy"


def test_rain_rows_skip_blank_slots():
    rows = nw._rain_rows([{"rfobscd": "1", "ymdhm": "202610182030", "rf": "13.0"}, {"rfobscd": "2", "ymdhm": "202610182030", "rf": " "}])
    assert list(rows) == ["1"] and rows["1"][1] == 13.0


def test_replay_rain_links_the_nearest_gauge_and_counts_regions():
    data = nw.overview(at=AT, limit=2000)
    rain = data["rain"]
    assert rain["available"] and rain["mode"] == "replay" and rain["raining"] > 0 and rain["heavy_or_above"] > 0
    assert rain["stations"] == sorted(rain["stations"], key=lambda row: -row["intensity_mm_h"])
    miho = nw.station_detail("3011665", at=AT)["rain_nearby"]
    assert miho["distance_km"] <= nw.RAIN_LINK_KM and miho["rain_1h_mm"] == 17.0 and miho["intensity"] == "heavy"
    assert data["counts"]["under_heavy_rain"] >= 1
    assert sum(item["raining"] for item in data["regions"]) <= rain["raining"]


def test_rain_tool_routes_and_reports_observed_rain_only():
    assert agent_watch.hints("지금 비 많이 오는 곳 어디야?")[0]["tool_name"] == "get_rain_status"
    assert agent_watch.hints("경남에 비 오는 곳 3곳")[0]["parameters"] == {"region": "경남", "limit": 3}
    assert agent_watch.hints("미호강교 비 와?")[0]["tool_name"] == "get_station_status"
    assert agent_watch.hints("비교해줘") == []
    request = agent_runner.AgentToolCallRequest(event_id="osong-2023", tool_name="get_rain_status", board="watch", observation_at=AT)
    result = agent_watch.run_tool("get_rain_status", request)
    assert result["view"]["layer"] == "rain" and result["wettest"] and result["gauges_under_heavy_rain_total"] >= 1
    text, _ = agent_watch.summarize([{"tool_name": "get_rain_status", "result": result, "order": 1}])
    assert "강한 비" in text and "예보" not in text
    assert not agent_watch.safe_model_answer("장흥군이 시간당 144.0mm로 가장 강합니다.", [{"tool_name": "get_rain_status", "result": result, "order": 1}])


def test_model_answer_with_a_wrong_stage_count_is_replaced():
    calls = [{"tool_name": "navigate_board", "order": 1, "result": {"counts": {"by_stage": {"normal": 22, "attention": 3, "advisory": 1}}}}]
    assert not agent_watch.safe_model_answer("정상 22곳, 주의보 3곳, 주의보 1곳입니다.", calls)
    assert agent_watch.safe_model_answer("정상 22곳, 관심 3곳, 주의보 1곳입니다.", calls)


def test_env_file_flag_is_set_only_after_the_file_is_read(monkeypatch):
    import sys
    import threading
    import time
    import types

    from app import llm_planner

    seen = []

    def slow_load(path, override=False):
        time.sleep(0.2)
        monkeypatch.setenv("FLOODOPS_TEST_ENV_RACE", "1")

    monkeypatch.setitem(sys.modules, "dotenv", types.SimpleNamespace(load_dotenv=slow_load))
    monkeypatch.setattr(llm_planner, "_env_file_loaded", False)
    monkeypatch.delenv("FLOODOPS_TEST_ENV_RACE", raising=False)

    def call():
        llm_planner._load_env_file_once()
        seen.append(bool(__import__("os").environ.get("FLOODOPS_TEST_ENV_RACE")))

    threads = [threading.Thread(target=call) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert seen == [True] * 4


def test_facility_catalog_keeps_facilities_without_a_gauge_and_riverside_entrances():
    catalog = nw.facility_catalog()
    tiers = {(f["group"], f["tier"]) for f in catalog}
    assert ("underpass", "operational") in tiers and ("underpass", "watch") in tiers and ("underpass", "rain_only") in tiers
    assert ("riverside", "watch") in tiers
    assert all(f["station_code"] is None for f in catalog if f["tier"] == "rain_only")
    assert all(f["distance_km"] <= nw.FACILITY_LINK_KM for f in catalog if f["tier"] == "watch")
    riverside = [f for f in catalog if f["group"] == "riverside"]
    assert len(riverside) >= 100 and all(f["river_name"] for f in riverside)
    assert len({f["facility_id"] for f in catalog}) == len(catalog)


def test_facility_status_orders_by_gauge_stage_then_rain():
    data = nw.facility_status(at=AT)
    rows = data["facilities"]
    assert rows[0]["facility_id"] == "gungpyeong2-underpass" or rows[0]["stage"] in ("warning", "planned_flood")
    ranks = [nw.STAGE_ORDER.index(row["stage"]) if row["stage"] in nw.STAGE_ORDER[2:] else 0 for row in rows]
    assert ranks == sorted(ranks, reverse=True)
    calm = [row for row in rows if row["stage"] not in nw.STAGE_ORDER[2:]]
    rain = [(row["rain_nearby"] or {}).get("intensity_mm_h") or 0 for row in calm]
    assert rain == sorted(rain, reverse=True)  # below 관심 the rain beside a facility leads, not the far-off minutes
    rain_only = next(row for row in rows if row["tier"] == "rain_only")
    assert rain_only["stage"] is None and rain_only["stage_label"] == "하천 관측소 없음"
    riverside = nw.facility_status(at=AT, group="riverside")
    assert riverside["counts"]["by_group"]["underpass"] == 0 and riverside["counts"]["total"] >= 100
    assert client.get("/api/watch/facility-status", params={"at": AT, "region": "충북", "group": "underpass", "limit": 3}).json()["filter"] == {"region": "충북", "group": "underpass"}


def test_rank_facilities_tool_takes_the_kind_from_the_users_words():
    assert agent_watch.hints("하천변 출입구 중 먼저 볼 곳 5곳 알려줘")[0] == {"tool_name": "rank_facilities", "parameters": {"group": "riverside", "limit": 5}}
    assert agent_watch.hints("충북 지하차도 중 위험한 곳 3곳")[0]["parameters"] == {"region": "충북", "group": "underpass", "limit": 3}
    with pytest.raises(ValueError):
        agent_watch.validate("rank_facilities", {"group": "riverside"}, "충북 지하차도 중 위험한 곳")
    request = agent_runner.AgentToolCallRequest(event_id="osong-2023", tool_name="rank_facilities", board="watch", observation_at=AT, group="riverside", limit=3)
    result = agent_watch.run_tool("rank_facilities", request)
    assert len(result["ranked"]) == 3 and all(row["group"] == "riverside" for row in result["ranked"])
    text, _ = agent_watch.summarize([{"tool_name": "rank_facilities", "result": result, "order": 1}])
    assert "하천변 출입구" in text and "1위" in text

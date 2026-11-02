"""권역(충청권·수도권 …) region filters and the season-record board tool."""

import json
from datetime import datetime

from fastapi.testclient import TestClient
import pytest

from app import agent_runner, agent_watch, national_watch as nw
from app.main import app

client = TestClient(app)
AT = "2023-07-15T06:00:00"


@pytest.fixture(autouse=True)
def replay(monkeypatch):
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")


def _offline(monkeypatch):
    monkeypatch.setattr(agent_runner, "_gemini_action", lambda context: (_ for _ in ()).throw(agent_runner.LlmPlannerUnavailable("offline")))


@pytest.mark.parametrize("text,region", [
    ("충청권 위험한 곳", "충청권"),
    ("충청도 지하차도", "충청권"),
    ("수도권 보여줘", "수도권"),
    ("호남권 비 오는 곳", "호남권"),
    ("전라도 현황", "호남권"),
    ("영남권 특보", "영남권"),
    ("경상도 시설", "영남권"),
    ("강원권 보여줘", "강원"),
    ("제주권 보여줘", "제주"),
    ("충청북도 보여줘", "충북"),   # a 시도 still wins over the 권역 word inside it
    ("전라남도 보여줘", "전남"),
    ("경상북도 보여줘", "경북"),
    ("경상자 몇 명이야", None),   # 경상 alone is an injury word, not 영남권
])
def test_match_region_reads_group_names_and_keeps_sido(text, region):
    assert nw.match_region(text) == region


def test_in_region_covers_the_group_members():
    assert nw.region_members("충청권") == ("대전", "세종", "충북", "충남")
    assert nw.region_members("충북") == ("충북",)
    assert nw.in_region("세종", "충청권") and not nw.in_region("서울", "충청권")
    assert nw.in_region("서울", None) and nw.in_region("충북", "충북") and not nw.in_region("충남", "충북")


def test_facility_status_filters_by_group_as_the_sum_of_its_members():
    group = nw.facility_status(at=AT, region="충청권")["counts"]["total"]
    members = sum(nw.facility_status(at=AT, region=sido)["counts"]["total"] for sido in nw.REGION_GROUPS["충청권"])
    assert group == members and group > 0
    assert all(row["region"] in nw.REGION_GROUPS["충청권"] for row in nw.facility_status(at=AT, region="충청권")["facilities"])
    overview = nw.overview(at=AT, region="충청권")
    assert overview["stations_total"] == sum(nw.overview(at=AT, region=sido)["stations_total"] for sido in nw.REGION_GROUPS["충청권"])


def test_watch_api_accepts_a_group_region():
    body = client.get("/api/watch/facility-status", params={"at": AT, "region": "충청권", "limit": 5}).json()
    assert body["filter"]["region"] == "충청권" and body["counts"]["total"] > 0
    assert all(row["region"] in nw.REGION_GROUPS["충청권"] for row in body["facilities"])


def test_rank_facilities_hint_and_validation_keep_the_group():
    question = "충청권 위험한 시설 3곳 알려줘"
    hint = agent_watch.hints(question)[0]
    assert hint == {"tool_name": "rank_facilities", "parameters": {"region": "충청권", "limit": 3}}
    assert agent_watch.validate("rank_facilities", {"region": "충청권", "limit": 3}, question) == {"region": "충청권", "limit": 3}
    with pytest.raises(ValueError):
        agent_watch.validate("rank_facilities", {"region": "충북"}, question)


def test_rank_facilities_tool_filters_to_the_group_and_keeps_the_board_national():
    request = agent_runner.AgentToolCallRequest(event_id="osong-2023", board="watch", observation_at=AT, region="충청권", limit=5)
    result = agent_watch.run_tool("rank_facilities", request)
    assert result["region"] == "충청권" and result["region_members"] == ["대전", "세종", "충북", "충남"]
    assert result["ranked"] and all(row["region"] in nw.REGION_GROUPS["충청권"] for row in result["ranked"])
    assert result["counts"]["total"] == sum(nw.facility_status(at=AT, region=sido)["counts"]["total"] for sido in nw.REGION_GROUPS["충청권"])
    view = result["view"]
    assert view["region"] is None and view["region_group"] == "충청권" and view["regions"] == ["대전", "세종", "충북", "충남"]


def test_board_agent_answers_a_group_region_without_falling_back_to_national(monkeypatch):
    _offline(monkeypatch)
    body = client.post("/api/agent/ask", json={"board": "watch", "message": "충청권 위험한 시설 3곳 알려줘", "observation_at": AT}).json()
    call = body["tool_calls"][0]
    assert call["tool_name"] == "rank_facilities" and call["parameters"]["region"] == "충청권"
    assert call["result"]["region"] == "충청권" and "충청권" in body["answer"]


# ---- season record -------------------------------------------------------------------------------
def _season() -> int:
    return max(2026, datetime.now().year)


def _write_log(tmp_path, lines):
    (tmp_path / f"{_season()}.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")


def _seoul_facility() -> str:
    return next(f["facility_id"] for f in nw.facility_catalog() if f["region"] == "서울")


def test_season_record_counts_the_logged_episodes_and_filters_by_region(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOODOPS_WATCH_LOG_DIR", str(tmp_path))
    osong, seoul = "gungpyeong2-underpass", _seoul_facility()
    year = _season()
    _write_log(tmp_path, [
        {"at": f"{year}-07-10T06:00:00", "total": 900, "facilities": {osong: [2, 0], seoul: [3, 1]}},
        {"at": f"{year}-07-10T06:10:00", "total": 900, "facilities": {osong: [3, 1]}},
        {"at": f"{year}-07-10T08:00:00", "total": 900, "facilities": {osong: [2, 0]}},
    ])
    whole = agent_watch.season_record(None, 5)
    assert whole["season"] == year and whole["coverage"]["snapshots"] == 3
    assert whole["counts"]["episodes"] == 3 and whole["counts"]["episodes_with_official"] == 2
    assert [row["facility_id"] for row in whole["ranked"]][0] == osong and whole["ranked"][0]["episodes"] == 2

    chungcheong = agent_watch.season_record("충청권", 5)
    assert [row["facility_id"] for row in chungcheong["ranked"]] == [osong]
    assert chungcheong["counts"]["episodes"] == 2 and chungcheong["counts"]["reached"] == {"주의": 1, "경계": 1, "심각": 0}
    assert chungcheong["counts"]["facilities"] == sum(1 for f in nw.facility_catalog() if f["region"] in nw.REGION_GROUPS["충청권"])

    text, refs = agent_watch.summarize([{"tool_name": "season_record", "result": chungcheong, "order": 1}])
    assert refs == [1] and "충청권" in text and "경보 구간은 2회" in text and "오경보로 확정하지 않습니다" in text


def test_season_record_without_a_log_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOODOPS_WATCH_LOG_DIR", str(tmp_path))
    result = agent_watch.season_record(None, 5)
    assert result["coverage"]["snapshots"] == 0 and result["ranked"] == []
    text, _ = agent_watch.summarize([{"tool_name": "season_record", "result": result, "order": 1}])
    assert "아직 없습니다" in text


def test_season_questions_route_to_the_season_record(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOODOPS_WATCH_LOG_DIR", str(tmp_path))
    question = "이번 장마 시즌 기록에서 경보 구간이 많았던 시설 5곳 알려줘"
    assert agent_watch.hints(question)[0] == {"tool_name": "season_record", "parameters": {"limit": 5}}
    assert agent_watch.hints("충청권 이번 장마 기록 보여줘")[0] == {"tool_name": "season_record", "parameters": {"region": "충청권"}}
    # A named operational facility's scorecard still wins over the season words.
    assert agent_watch.hints("이번 장마 궁평2지하차도 규칙 성적표 보여줘")[0]["tool_name"] == "rule_scorecard"
    assert any(example["workflow"] == "season_record" for example in client.get("/api/agent/examples", params={"board": "watch"}).json())
    _offline(monkeypatch)
    body = client.post("/api/agent/ask", json={"board": "watch", "message": question}).json()
    assert body["status"] == "ANSWERED" and body["tool_calls"][0]["tool_name"] == "season_record"
    assert "시즌 기록이 아직 없습니다" in body["answer"]

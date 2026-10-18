"""Board-operator Agent tools over the national watch: navigate, rank, diff, brief, and score a rule.

Every number comes from national_watch / twin. The model only picks a tool and copies the user's own
region, station, facility or time words into its parameters; validate() rejects anything else.
"""

from __future__ import annotations

import re
from typing import Any

from . import national_watch as nw

TOOL_NAMES = {"get_watch_overview", "navigate_board", "rank_priority", "summarize_changes", "get_station_status",
              "draft_situation_report", "rule_scorecard", "get_rain_status"}
PARAMETERS: dict[str, set[str]] = {
    "get_watch_overview": {"region", "min_stage"},
    "navigate_board": {"region", "station", "facility", "min_stage"},
    "rank_priority": {"region", "limit"},
    "summarize_changes": {"since_min", "region"},
    "get_station_status": {"station"},
    "draft_situation_report": {"region"},
    "rule_scorecard": {"facility"},
    "get_rain_status": {"region", "limit"},
}
EXAMPLES = [
    {"workflow": "watch_overview", "label": "전국 현황", "question": "지금 전국에서 주의보 이상인 관측소가 몇 곳이야?"},
    {"workflow": "rank_priority", "label": "우선순위", "question": "지금 가장 위험한 곳 5곳 알려줘"},
    {"workflow": "navigate_board", "label": "지역 이동", "question": "충북 보여줘"},
    {"workflow": "station_status", "label": "관측소 상태", "question": "미호강교 지금 몇 단계야?"},
    {"workflow": "summarize_changes", "label": "변화 요약", "question": "지난 1시간 동안 뭐가 바뀌었어?"},
    {"workflow": "situation_report", "label": "상황 보고", "question": "지금 상황 보고 초안 써줘"},
    {"workflow": "rule_scorecard", "label": "규칙 성적표", "question": "궁평2지하차도 규칙 성적표 보여줘"},
    {"workflow": "rain_status", "label": "강우", "question": "지금 비 많이 오는 곳 어디야?"},
]
WATCH_CAVEAT = "감시 등급 연결은 5 km 안 가장 가까운 관측소 기준이며 그 관측소가 시설 유입을 대표하는지는 검증하지 않았습니다."
BASELINE_CAVEAT = "남은 분은 최근 상승 속도를 그대로 늘린 기준선이며 예보가 아닙니다."
RAIN_CAVEAT = "강우는 하천 수위에 시간차를 두고 반영되며, 강우만으로 단계나 침수를 판정하지 않습니다."

_STAGE_WORDS = [("계획홍수위", "planned_flood"), ("경보", "warning"), ("주의보", "advisory"), ("관심", "attention")]


def tools() -> list[dict[str, Any]]:
    descriptions = [
        ("get_watch_overview", "전국 또는 한 지역의 관측소 단계 분포·상승 중 관측소 수·연결 시설 수를 센다. 몇 곳인지, 전체 현황을 물을 때.",
         "region: 사용자가 쓴 시도 이름(강원·충북 등). min_stage: 사용자가 쓴 단계(관심·주의보·경보·계획홍수위). 쓰지 않으면 생략.",
         "단계별 관측소 수, 상승 중 수, 자료 품질 수, 지역별 최고 단계, 상위 관측소.", "시설 침수 여부, 예보, 통제 명령."),
        ("navigate_board", "화면을 지역·관측소·시설로 옮긴다. '○○ 보여줘', '○○로 가', '○○ 지도에서' 같은 이동 요청.",
         "region: 사용자가 쓴 시도. station: 사용자가 쓴 관측소 이름. facility: 사용자가 쓴 시설 이름. min_stage: 사용자가 쓴 단계. 하나 이상.",
         "이동한 위치와 그곳의 현재 단계·수위·연결 시설.", "이동 대상이 아닌 다른 지역의 수치."),
        ("rank_priority", "계획홍수위까지 남은 분과 단계로 관측소를 정렬한다. 가장 위험한 곳, 먼저 볼 곳, 상위 N곳을 물을 때.",
         "region: 사용자가 쓴 시도(없으면 전국). limit: 사용자가 쓴 개수(기본 5).", "순위별 관측소·단계·수위·상승 속도·남은 분·연결 시설.", "순위 밖 관측소의 안전, 예보."),
        ("summarize_changes", "최근 N분 사이 단계가 오르거나 내린 관측소와 새로 빠르게 오르는 관측소를 비교한다. 뭐가 바뀌었는지 물을 때.",
         "since_min: 사용자가 쓴 분(‘1시간’은 60, 기본 60). region: 사용자가 쓴 시도.", "단계 상승·하강 관측소, 새로 오르는 관측소, 비교 시각.", "원인(강우·방류)의 단정, 예보."),
        ("get_station_status", "관측소 한 곳의 지금 단계·수위·상승 속도·계획홍수위까지 남은 분·연결 시설을 설명한다. 특정 관측소를 물을 때.",
         "station: 사용자가 쓴 관측소 이름(예: 미호강교) 또는 코드.", "관측 시각·수위·단계·속도·남은 분·연결 시설과 등급.", "시설 침수 여부, 도달 시각 확정, 통제 명령."),
        ("draft_situation_report", "현재 시각 기준 상황 보고에 넣을 수치 묶음(단계 분포, 상위 관측소, 운영 시설 상태, 자료 품질)을 모은다. 보고·브리핑·정리를 요청할 때.",
         "region: 사용자가 쓴 시도(없으면 전국).", "보고 시각, 단계별 수, 상위 5곳, 운영 등록 시설 상태, 품질 주의, 한계 문구.", "피해·사망, 원인 단정, 예보."),
        ("rule_scorecard", "운영 등록 시설의 통제 검토 규칙을 적중·누락·오경보 후보·근접으로 나눠 채점한다(Barnes et al. 2007의 네 분류를 따른다). 규칙이 얼마나 믿을 만한지, 성적표를 물을 때.",
         "facility: 사용자가 쓴 운영 시설 이름(예: 궁평2지하차도).", "기준 사건 적중 여부와 선행 분, 다른 해 권고 구간(오경보 후보) 수, 권고 없이 경보 수위에 닿은 해(근접) 수, 계획홍수위 미도달 권고 수.", "오경보 확정(통제 기록 대조 전), 피해 감소, 최적 기준 확정."),
        ("get_rain_status", "지금 비가 오는 강우 관측소와 강도(최근 10분 강우의 시간당 환산), 강한 비 아래에 있는 하천 관측소를 센다. 비·강우·호우·폭우를 물을 때.",
         "region: 사용자가 쓴 시도(없으면 전국). limit: 사용자가 쓴 개수(기본 5).",
         "강우 관측소 수, 비 오는 곳 수, 강도별 수, 많이 오는 곳 상위 N곳, 강한 비 아래 하천 관측소의 단계·상승 속도.", "앞으로 내릴 비(예보), 침수 발생, 수위 상승 시각."),
    ]
    return [{"name": name, "description": description, "input_fields": sorted(PARAMETERS[name]),
             "output": "national watch evidence with provenance and limitations", "use_when": description,
             "parameters": parameters, "can_say": can_say, "cannot_say": cannot_say,
             "examples": [example["question"] for example in EXAMPLES if example["workflow"] in name or name.endswith(example["workflow"])][:2]}
            for name, description, parameters, can_say, cannot_say in descriptions]


# ---- routing -------------------------------------------------------------------------------------
_MOVE = re.compile(r"보여\s*줘|보여줘|가자|이동|로\s*가|으로\s*가|지도에서|띄워|열어")
_RANK = re.compile(r"위험한|우선|먼저\s*볼|상위|순위|top|가장")
_CHANGE = re.compile(r"바뀌|변화|달라|지난\s*\d|최근\s*\d|새로")
_REPORT = re.compile(r"보고|브리핑|정리해|요약해")
_SCORE = re.compile(r"성적|적중|오경보|근접|채점|믿을")
_RAIN = re.compile(r"강우|호우|폭우|소나기|빗줄기|비\s*(?:가|는|도)?\s*(?:많이|오|와|내리|온|쏟|퍼붓)")
_OVERVIEW = re.compile(r"몇\s*곳|현황|전체|전국|몇\s*개")
_STATUS = re.compile(r"단계|수위|남았|상태|여유|얼마")


def _written_stage(message: str) -> str | None:
    for word, stage in _STAGE_WORDS:
        if word in message:
            return stage
    return None


def _written_minutes(message: str) -> int | None:
    hours = re.search(r"(\d{1,2})\s*시간", message)
    if hours:
        return int(hours.group(1)) * 60
    minutes = re.search(r"(\d{1,4})\s*분", message)
    return int(minutes.group(1)) if minutes else None


def _written_limit(message: str) -> int | None:
    match = re.search(r"(\d{1,2})\s*(?:곳|개|군데|위)", message)
    return int(match.group(1)) if match else None


def hints(message: str) -> list[dict[str, Any]]:
    region = nw.match_region(message)
    station = nw.find_station(message)
    facility = nw.find_facility(message)
    stage = _written_stage(message)
    out: list[dict[str, Any]] = []

    def add(name: str, **params: Any) -> None:
        out.append({"tool_name": name, "parameters": {k: v for k, v in params.items() if v is not None}})

    if _SCORE.search(message) and facility and facility["tier"] == "operational":
        add("rule_scorecard", facility=facility["name"])
    elif _RAIN.search(message) and station:
        add("get_station_status", station=station.short_name)
    elif _RAIN.search(message) and not facility:
        add("get_rain_status", region=region, limit=_written_limit(message))
    elif _MOVE.search(message) and (region or station or facility):
        add("navigate_board", region=region, station=station.short_name if station else None, facility=facility["name"] if facility else None, min_stage=stage)
    elif _CHANGE.search(message):
        add("summarize_changes", since_min=_written_minutes(message), region=region)
    elif _REPORT.search(message):
        add("draft_situation_report", region=region)
    elif _RANK.search(message):
        add("rank_priority", region=region, limit=_written_limit(message))
    elif station and _STATUS.search(message):
        add("get_station_status", station=station.short_name)
    elif facility and _STATUS.search(message):
        add("navigate_board", facility=facility["name"])
    elif _OVERVIEW.search(message) or stage:
        add("get_watch_overview", region=region, min_stage=stage)
    return out


def validate(name: str, params: dict[str, Any], supplied: str) -> dict[str, Any]:
    """Every parameter must be the user's own words resolved against the catalogue."""
    if name not in TOOL_NAMES:
        raise ValueError("Unknown watch tool.")
    clean: dict[str, Any] = {}
    if params.get("region") is not None:
        region = nw.match_region(str(params["region"]))
        if region is None or region != nw.match_region(supplied):
            raise ValueError("The region must be a 시도 the user named.")
        clean["region"] = region
    if params.get("station") is not None:
        station = nw.find_station(str(params["station"])) or nw.find_station(supplied)
        if station is None or (station.short_name not in supplied and station.name not in supplied and station.code not in supplied):
            raise ValueError("The station must be one the user named.")
        clean["station"] = station.code
    if params.get("facility") is not None:
        facility = nw.find_facility(str(params["facility"])) or nw.find_facility(supplied)
        if facility is None or facility["name"] not in supplied:
            raise ValueError("The facility must be one the user named.")
        clean["facility"] = facility["facility_id"]
    if params.get("min_stage") is not None:
        stage = params["min_stage"] if params["min_stage"] in nw.STAGE_ORDER else _written_stage(str(params["min_stage"]))
        if stage is None or stage != _written_stage(supplied):
            raise ValueError("The stage must be one the user wrote.")
        clean["min_stage"] = stage
    if params.get("limit") is not None:
        limit = int(params["limit"]) if str(params["limit"]).isdigit() else None
        if limit is None or limit != _written_limit(supplied) or not 1 <= limit <= 20:
            raise ValueError("The count must appear in the user's question (1–20).")
        clean["limit"] = limit
    if params.get("since_min") is not None:
        minutes = int(params["since_min"]) if str(params["since_min"]).isdigit() else None
        if minutes is None or minutes != _written_minutes(supplied) or not 10 <= minutes <= 1440:
            raise ValueError("The time span must appear in the user's question (10–1440 minutes).")
        clean["since_min"] = minutes
    if name == "navigate_board" and not any(key in clean for key in ("region", "station", "facility", "min_stage")):
        raise ValueError("navigate_board needs a region, station, facility or stage the user named.")
    if name == "get_station_status" and "station" not in clean:
        raise ValueError("get_station_status needs a station the user named.")
    if name == "rule_scorecard" and "facility" not in clean:
        raise ValueError("rule_scorecard needs an operational facility the user named.")
    return clean


# ---- execution ------------------------------------------------------------------------------------
def _station_brief(row: dict[str, Any]) -> dict[str, Any]:
    keys = ("code", "name", "region", "stage", "stage_label", "quality", "rate_m_per_10min", "rate_window_min", "rise_label",
            "margin_to_planned_flood_m", "minutes_to_planned_flood", "flood_forecast")
    brief = {key: row.get(key) for key in keys}
    brief["observation"] = row.get("observation")
    brief["levels_m"] = row.get("levels_m")
    brief["facilities"] = [{"facility_id": f["facility_id"], "name": f["name"], "tier": f["tier"], "distance_km": f.get("distance_km")} for f in row.get("facilities", [])]
    brief["rain_nearby"] = row.get("rain_nearby")
    return brief


def _view(region: str | None = None, station: dict[str, Any] | None = None, facility: dict[str, Any] | None = None, min_stage: str | None = None,
          layer: str | None = None) -> dict[str, Any]:
    view: dict[str, Any] = {"region": region, "min_stage": min_stage, "station_code": None, "facility_id": None, "center": None, "zoom": None, "layer": layer}
    if facility:
        view.update(station_code=facility["station_code"], facility_id=facility["facility_id"], center=[facility["lon"], facility["lat"]], zoom=13)
    elif station:
        view.update(station_code=station["code"], center=[station["lon"], station["lat"]], zoom=12)
    elif region:
        view.update(zoom=8)
    return view


def run_tool(name: str, request: Any) -> dict[str, Any]:
    if name not in TOOL_NAMES:
        raise KeyError("Unknown watch Agent tool.")
    at = request.observation_at
    region = getattr(request, "region", None)
    min_stage = getattr(request, "min_stage", None)
    if name == "get_watch_overview":
        data = nw.overview(at, region, min_stage, limit=10)
        return {"mode": data["mode"], "at": data["at"], "observed_at": data["observed_at"], "source": data["source"], "filter": data["filter"],
                "stations_total": data["stations_total"], "stations_observed": data["stations_observed"],
                "counts": data["counts"], "regions": data["regions"], "top": [_station_brief(row) for row in data["stations"][:10]],
                "view": _view(region=region, min_stage=min_stage),
                "coverage_note": "NATIONAL_WATCH: gauge stages against each station's official levels; facility links are watch-tier.",
                "limitations": data["limitations"]}
    if name == "rank_priority":
        limit = getattr(request, "limit", None) or 5
        data = nw.overview(at, region, None, limit=limit)
        return {"mode": data["mode"], "at": data["at"], "region": region, "limit": limit,
                "ranked": [{"rank": index + 1, **_station_brief(row)} for index, row in enumerate(data["stations"][:limit])],
                "view": _view(region=region), "coverage_note": "NATIONAL_WATCH: ordered by stage, then minutes to planned flood, then rate.",
                "limitations": [*data["limitations"], "순위는 관측소 기준이며 시설의 실제 위험 순위가 아니다."]}
    if name == "summarize_changes":
        since = getattr(request, "since_min", None) or 60
        data = nw.changes(since, at, region)
        return {**data, "view": _view(region=region), "coverage_note": "NATIONAL_WATCH_DIFF: two snapshots compared; causes are not attributed.",
                "limitations": ["단계 변화는 관측값 비교이며 강우·방류 원인을 단정하지 않는다.", BASELINE_CAVEAT]}
    if name == "get_station_status":
        detail = nw.station_detail(getattr(request, "station"), at)
        return {**_station_brief(detail), "mode": detail["mode"], "at": detail["at"], "recent": detail["recent"][-7:],
                "view": _view(station=detail),
                "coverage_note": "HISTORICAL_REPLAY: stored hourly observations." if detail["mode"] == "replay" else "LIVE_OBSERVATION: check observation age before interpretation.",
                "limitations": ["단계는 관측소 공식 기준 수위 기준이며 시설 침수심이 아니다.", BASELINE_CAVEAT, WATCH_CAVEAT]}
    if name == "navigate_board":
        station = None
        facility = None
        if getattr(request, "facility", None):
            facility = nw.facility_index()[request.facility]
            station = nw.station_detail(facility["station_code"], at)
        elif getattr(request, "station", None):
            station = nw.station_detail(request.station, at)
        data = nw.overview(at, region or (station["region"] if station else None), min_stage, limit=5) if not station else None
        result: dict[str, Any] = {"view": _view(region=region, station=station, facility=facility, min_stage=min_stage), "mode": (station or data)["mode"],
                                  "moved_to": facility["name"] if facility else station["name"] if station else region or nw.STAGE_KO.get(min_stage or "", "전국"),
                                  "coverage_note": "NAVIGATION: the board follows this view; numbers describe the destination only.",
                                  "limitations": [WATCH_CAVEAT if (facility or station) else "지역 이동은 화면 범위만 바꾼다."]}
        if station:
            result["station"] = _station_brief(station)
        if facility:
            result["facility"] = {key: facility.get(key) for key in ("facility_id", "name", "tier", "distance_km", "region", "sgg", "event_id")}
        if data:
            result["counts"] = data["counts"]
            result["top"] = [_station_brief(row) for row in data["stations"][:5]]
        return result
    if name == "draft_situation_report":
        data = nw.overview(at, region, None, limit=5)
        from .twin import FACILITIES, facility_status
        operational = []
        for facility in FACILITIES.values():
            try:
                status = facility_status(facility["id"], at)
            except Exception:  # a live gauge outage must not block the rest of the brief
                status = {"status": "UNAVAILABLE"}
            operational.append({"facility_id": facility["id"], "name": facility["name"], "status": status.get("status"), "stage_label": status.get("stage_label"),
                                "recommendation": status.get("recommendation"), "minutes_to_planned_flood": status.get("minutes_to_planned_flood"),
                                "observation_time": (status.get("observation") or {}).get("time")})
        counts = data["counts"]
        return {"mode": data["mode"], "at": data["at"], "observed_at": data["observed_at"], "region": region or "전국",
                "stations_total": data["stations_total"], "stations_observed": data["stations_observed"],
                "by_stage": counts["by_stage"], "rising": counts["rising"], "quality": counts["quality"],
                "top": [_station_brief(row) for row in data["stations"][:5]], "operational_facilities": operational,
                "regions_at_advisory_or_above": [r for r in data["regions"] if r["advisory_or_above"]],
                "view": _view(region=region),
                "coverage_note": "SITUATION_BRIEF: numbers only; the wording of the report is the reader's responsibility.",
                "limitations": [*data["limitations"], "보고 문안은 수치 근거를 인용하되 피해·원인을 단정하지 않는다."]}
    if name == "rule_scorecard":
        return scorecard(getattr(request, "facility"))
    if name == "get_rain_status":
        limit = getattr(request, "limit", None) or 5
        data = nw.overview(at, region, None, limit=2000)
        rain = data["rain"]
        rained_on = [row for row in data["stations"] if ((row.get("rain_nearby") or {}).get("intensity_mm_h") or 0) >= nw.RAIN_CLASSES[1][0]]
        return {"mode": rain["mode"], "at": data["at"], "observed_at": rain["observed_at"], "region": region or "전국", "available": rain["available"],
                "basis": rain["basis"], "gauges_reporting": rain["gauges_reporting"], "raining": rain["raining"], "heavy_or_above": rain["heavy_or_above"],
                "by_intensity": rain["by_intensity"],
                "wettest": [{key: row[key] for key in ("code", "name", "region", "rain_10m_mm", "rain_1h_mm", "rain_1h_basis", "intensity_mm_h", "intensity_label", "time")}
                            for row in rain["stations"][:limit]],
                "gauges_under_heavy_rain": [{**_station_brief(row), "rain_nearby": row.get("rain_nearby")} for row in rained_on[:limit]],
                "gauges_under_heavy_rain_total": len(rained_on),
                "view": _view(region=region, layer="rain"),
                "coverage_note": "RAIN_OBSERVATION: observed rain only; no forecast and no flood attribution.",
                "limitations": [*rain["limitations"], RAIN_CAVEAT]}
    raise KeyError(name)


def scorecard(facility_id: str) -> dict[str, Any]:
    """Barnes et al. (2007) four-way warning verification, adapted to one facility's stored seasons."""
    from . import twin
    facility = twin.FACILITIES.get(facility_id)
    if facility is None:
        raise ValueError("rule_scorecard only covers operational facilities with a registered rule.")
    review = twin.criteria_review(facility_id, None, None)
    warning = (review.get("station") or {}).get("levels_m", {}).get("warning")
    lead = (review.get("lead_minutes") or {}).get("underpass_inflow")
    hit = 1 if lead is not None and lead > 0 else 0
    miss = 0 if hit else 1
    other_episodes = [e for e in review.get("episodes", []) if not e.get("reference_event")]
    false_alarm_candidates = len(other_episodes)
    review_below_pfh = sum(1 for e in other_episodes if e.get("peak_stage") != "planned_flood")
    near_miss_years = [row["year"] for row in review.get("by_year", []) if not row.get("reference_event") and not row.get("episodes")
                       and warning is not None and (row.get("max_water_level_m") or 0) >= warning]
    return {
        "facility_id": facility_id, "facility": facility["name"], "rule": review.get("current_rule"),
        "reference_event": review.get("reference_event"), "first_review": review.get("first_review"), "lead_minutes": review.get("lead_minutes"),
        "scorecard": {
            "hit": hit, "miss": miss, "false_alarm_candidates": false_alarm_candidates, "review_without_planned_flood": review_below_pfh,
            "close_call_years": near_miss_years, "years_covered": [row["year"] for row in review.get("by_year", [])],
        },
        "other_episodes": [{key: e.get(key) for key in ("start", "end", "review_minutes", "peak_water_level_m", "peak_stage")} for e in other_episodes][:10],
        "method": "Barnes et al. 2007 (Weather and Forecasting 22) 네 분류: 적중·누락·오경보·근접. 사건이 1건이라 적중·누락은 기준 사건 하나로만 센다.",
        "coverage_note": "BACKTEST_SWEEP: other-year review episodes were not matched with closure records; they are candidates, not confirmed false alarms.",
        "limitations": ["다른 해 권고 구간은 통제·침수 기록과 대조하지 않아 오경보로 확정하지 않는다.",
                        "근접은 권고 없이 경보 수위에 닿은 해를 센 것이며 실제 침수 여부는 확인하지 않았다.",
                        "2026년 보관 수위와 현재 기준값으로 계산했다."],
    }


# ---- deterministic rendering ------------------------------------------------------------------------
def _fmt_station(row: dict[str, Any]) -> str:
    obs = row.get("observation") or {}
    bits = [f"{row.get('name')} {row.get('stage_label') or '기준 없음'}"]
    if obs:
        bits.append(f"{obs.get('water_level_m')} m({obs.get('time', '')[11:16]})")
    if row.get("rate_m_per_10min") is not None:
        bits.append(f"{row['rate_m_per_10min']:+.2f} m/10분")
    if row.get("minutes_to_planned_flood") is not None:
        bits.append(f"계획홍수위까지 {row['minutes_to_planned_flood']}분")
    if row.get("facilities"):
        bits.append("연결 시설 " + "·".join(f["name"] for f in row["facilities"][:3]))
    rain = row.get("rain_nearby") or {}
    if (rain.get("intensity_mm_h") or 0) > 0:
        amount = f"10분 {rain['rain_10m_mm']} mm" if rain.get("rain_10m_mm") is not None else f"1시간 {rain.get('rain_1h_mm')} mm"
        bits.append(f"근처 강우 {rain.get('intensity_label')}({amount}, {rain.get('distance_km')} km)")
    return " · ".join(bits)


def summarize(calls: list[dict[str, Any]]) -> tuple[str, list[int]]:
    sentences, evidence = [], []
    for call in calls:
        name, result, order = call["tool_name"], call["result"], call["order"]
        text = ""
        if name in {"get_watch_overview", "draft_situation_report"}:
            counts = result.get("counts", result)
            by = counts.get("by_stage", result.get("by_stage", {}))
            scope = result.get("filter", {}).get("region") or result.get("region") or "전국"
            text = (f"{result.get('observed_at') or result.get('at')} 기준 {scope} 관측소 {result.get('stations_total', '')}곳 중 "
                    f"계획홍수위 {by.get('planned_flood', 0)}곳, 경보 {by.get('warning', 0)}곳, 주의보 {by.get('advisory', 0)}곳, 관심 {by.get('attention', 0)}곳이고 "
                    f"상승 중은 {counts.get('rising', result.get('rising', 0))}곳입니다.")
            top = result.get("top") or []
            if top:
                text += " 상위: " + "; ".join(_fmt_station(row) for row in top[:3]) + "."
            if name == "draft_situation_report":
                for item in result.get("operational_facilities", []):
                    text += f" 운영 시설 {item['name']}: {item.get('stage_label') or item.get('status')}, 권고 {item.get('recommendation') or '—'}."
        elif name == "rank_priority":
            rows = result.get("ranked", [])
            text = f"{result.get('region') or '전국'} 우선순위 {len(rows)}곳: " + "; ".join(f"{row['rank']}위 {_fmt_station(row)}" for row in rows) + "."
        elif name == "summarize_changes":
            if not result.get("available"):
                text = result.get("note", "비교할 이전 자료가 없습니다.")
            else:
                text = (f"{result.get('compared_to', '')[11:16]}→{result.get('at', '')[11:16]} 사이 단계 상승 {len(result.get('stage_up', []))}곳, "
                        f"하강 {len(result.get('stage_down', []))}곳, 새로 빠르게 오르는 곳 {len(result.get('new_rising', []))}곳입니다.")
                ups = result.get("stage_up", [])[:3]
                if ups:
                    text += " 상승: " + "; ".join(f"{u['name']} {nw.STAGE_KO.get(u['from'], u['from'])}→{nw.STAGE_KO.get(u['to'], u['to'])} ({u['delta_m']:+.2f} m)" for u in ups) + "."
        elif name == "get_station_status":
            text = _fmt_station(result) + "."
            if not result.get("rain_nearby"):
                text += " 10 km 안에 강우 관측값이 있는 관측소가 없습니다."
            elif not (result["rain_nearby"].get("intensity_mm_h") or 0):
                text += f" 근처 강우 관측소({result['rain_nearby'].get('name')})에는 비가 관측되지 않았습니다."
            if result.get("quality") != "fresh":
                text += f" 관측 품질이 {result.get('quality')}라 현재 판단에 쓰기 어렵습니다."
        elif name == "navigate_board":
            text = f"{result.get('moved_to')}(으)로 이동했습니다."
            if result.get("station"):
                text += " " + _fmt_station(result["station"]) + "."
            elif result.get("counts"):
                by = result["counts"]["by_stage"]
                text += f" 이 범위의 경보 {by.get('warning', 0)}곳, 주의보 {by.get('advisory', 0)}곳입니다."
        elif name == "rule_scorecard":
            card = result.get("scorecard", {})
            text = (f"{result.get('facility')} 규칙 성적표: 기준 사건 적중 {card.get('hit')}·누락 {card.get('miss')}, 다른 해 권고 구간(오경보 후보) {card.get('false_alarm_candidates')}건, "
                    f"권고 없이 경보 수위에 닿은 해(근접) {len(card.get('close_call_years', []))}개({', '.join(map(str, card.get('close_call_years', []))) or '없음'}), "
                    f"계획홍수위 미도달 권고 {card.get('review_without_planned_flood')}건입니다. 다른 해 권고는 통제 기록과 대조 전이라 오경보로 확정하지 않습니다.")
        elif name == "get_rain_status":
            if not result.get("available"):
                text = "이 시각의 강우 관측 자료가 없습니다."
            else:
                text = (f"{(result.get('observed_at') or '')[11:16]} 기준 {result.get('region')} 강우 관측소 {result.get('gauges_reporting')}곳 중 "
                        f"{result.get('raining')}곳에서 비가 관측됐고, 강한 비(시간당 15 mm 이상) 이상은 {result.get('heavy_or_above')}곳입니다.")
                wet = result.get("wettest") or []
                if wet:
                    text += " 많이 오는 곳: " + "; ".join(
                        f"{row['name']} {row['intensity_label']}"
                        + (f"(10분 {row['rain_10m_mm']} mm)" if row.get("rain_10m_mm") is not None else f"(1시간 {row['rain_1h_mm']} mm)")
                        for row in wet[:5]) + "."
                under = result.get("gauges_under_heavy_rain") or []
                text += f" 강한 비 아래 하천 관측소는 {result.get('gauges_under_heavy_rain_total', 0)}곳"
                text += (": " + "; ".join(_fmt_station(row) for row in under[:3]) + ".") if under else "입니다."
        if text:
            sentences.append(f"{text} [{order}]")
            evidence.append(order)
    return "\n".join(sentences), evidence


_STAGE_COUNT = re.compile(r"(계획홍수위|경보|주의보|관심|정상)\s*(?:단계\s*)?(\d+)\s*곳")
_STAGE_KEY = {"계획홍수위": "planned_flood", "경보": "warning", "주의보": "advisory", "관심": "attention", "정상": "normal"}


def _stage_counts_match(answer: str, calls: list[dict[str, Any]]) -> bool:
    """A model sentence such as "주의보 3곳" must match a stage count a tool returned; models swap 관심 and 주의보."""
    tallies = [by for call in calls for by in ((call["result"].get("counts") or {}).get("by_stage"), call["result"].get("by_stage")) if isinstance(by, dict)]
    if not tallies:
        return True
    return all(any(by.get(_STAGE_KEY[word]) == int(count) for by in tallies) for word, count in _STAGE_COUNT.findall(answer))


def safe_model_answer(answer: str, calls: list[dict[str, Any]]) -> bool:
    if re.search(r"안전합니다|위험이?\s*없|통제(?:를)?\s*(?:실행|승인|완료)|자동\s*차단|침수가?\s*없|피해가?\s*줄|대피\s*성공|침수될\s*것|넘칠\s*것", answer):
        return False
    if not _stage_counts_match(answer, calls):
        return False
    # Models turn the 10-minute ×6 conversion into "시간당 144 mm" and mix up the intensity bins; rain is always read out by the tool summary.
    if any(call["tool_name"] == "get_rain_status" for call in calls):
        return False
    for call in calls:
        if call["tool_name"] == "get_station_status" and call["result"].get("quality") not in (None, "fresh"):
            return False
    return True


FORECAST_ANSWER = ("앞으로 내릴 비나 침수를 예측하는 도구는 연결돼 있지 않습니다. 감시 보드는 지금 관측된 수위와 단계, "
                   "현재 상승 속도로 계획홍수위까지 남은 분(기준선)만 보여줍니다.")


def unavailable_answer() -> tuple[str, str]:
    return ("감시 보드 에이전트는 전국·지역 현황, 우선순위, 관측소 상태, 최근 변화, 상황 보고 수치, 운영 시설 규칙 성적표를 설명하고 화면을 옮깁니다. "
            "예보, 시설 침수 여부, 피해, 통제 실행은 계산하거나 수행하지 않습니다.",
            "No registered watch tool computes the requested effect.")

"""Board-operator Agent tools over the national watch: navigate, rank, diff, brief, and score a rule.

Every number comes from national_watch / twin. The model only picks a tool and copies the user's own
region, station, facility or time words into its parameters; validate() rejects anything else.
"""

from __future__ import annotations

import re
from typing import Any

from . import national_watch as nw

TOOL_NAMES = {"get_watch_overview", "navigate_board", "rank_priority", "summarize_changes", "get_station_status",
              "draft_situation_report", "rule_scorecard", "get_rain_status", "rank_facilities", "get_official_forecasts", "validation_cases", "post_event_review"}
PARAMETERS: dict[str, set[str]] = {
    "get_watch_overview": {"region", "min_stage"},
    "navigate_board": {"region", "station", "facility", "min_stage"},
    "rank_priority": {"region", "limit"},
    "summarize_changes": {"since_min", "region"},
    "get_station_status": {"station"},
    "draft_situation_report": {"region"},
    "rule_scorecard": {"facility"},
    "get_rain_status": {"region", "limit"},
    "rank_facilities": {"region", "group", "driver", "limit"},
    "get_official_forecasts": {"region"},
    "validation_cases": {"region"},
    "post_event_review": {"region", "case_id"},
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
    {"workflow": "rank_facilities", "label": "시설 우선순위", "question": "하천변 출입구 중 먼저 볼 곳 5곳 알려줘"},
    {"workflow": "rank_facilities", "label": "내수형 시설", "question": "내수형 중 비 많이 오는 곳 5곳 알려줘"},
    {"workflow": "get_official_forecasts", "label": "공식 특보", "question": "지금 홍수특보 내려진 곳 있어?"},
    {"workflow": "validation_cases", "label": "사례 검증", "question": "대전 사례에서 규칙이 실제 통제보다 빨랐어?"},
    {"workflow": "post_event_review", "label": "사후 검토", "question": "오송 사건 사후 검토 보고서 작성해줘"},
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
        ("rank_facilities", "시설을 잠그는 원인에 맞춰 하천형은 연결 수위, 내수형은 시설 근처 강우로 순위를 낸다. 위험한 시설, 먼저 볼 지하차도, 비가 많이 오는 내수형을 물을 때.",
         "region: 사용자가 쓴 시도(없으면 전국). group: 사용자가 '지하차도'라고 쓰면 underpass, '하천변·둔치·출입구·하상도로'라고 쓰면 riverside(쓰지 않으면 생략). driver: '하천형'이면 river, '내수형'이면 pluvial(쓰지 않으면 생략). limit: 사용자가 쓴 개수(기본 5).",
         "시설 이름·종류·지역, 하천형·내수형 분류, 위험 단계, 판단 이유, 하천 관측소와 거리, 계획홍수위까지 남은 분, 주변 1·3시간 강우.", "시설 침수 여부, 통제 실행, 배수·펌프 용량에 따른 실제 침수 판단."),
        ("get_official_forecasts", "홍수통제소가 낸 공식 홍수주의보·홍수경보 중인 관측소를 센다(실시간, 재생 시각이면 그 시각의 발령 이력). 특보·홍수경보·홍수주의보·발령을 물을 때.",
         "region: 사용자가 쓴 시도(없으면 전국).",
         "특보 종류별 관측소 수, 관측소별 발령 시각·발령 시 수위·예상 수위·예상 시각·경과 분.", "특보 문안 밖의 예보, 시설 침수 여부, 통제 실행."),
        ("validation_cases", "과거 사건(오송 2023, 대전 2020·2023·2024)에서 시설 위험 규칙과 공식 특보가 실제 통제·유입보다 몇 분 먼저였는지 보여준다. 검증·사례·규칙이 실제 통제보다 빨랐는지 물을 때.",
         "region: 사용자가 쓴 시도(대전·충북, 없으면 전부).",
         "사례별 기준 시각(통제·유입)과 정밀도, 공식 주의보·경보·시설 주의·경계 첫 시각과 선행 분, 기준 시각에 주의 이상이던 같은 지역 시설 수.",
         "보도에 없는 분 단위 통제 시각, 기준을 바꾸면 어떻게 되는지(재계산 안 함), 다른 사건 일반화."),
        ("post_event_review", "저장된 오송·대전 사례의 사건 기준, 공식 특보, 시설 위험 재생 신호를 한데 묶어 사후 검토 초안을 만든다. PERC에서 영감을 받은 증거 제한형 데스크 검토이며 사후 검토·복기·PERC 보고서를 요청할 때.",
         "case_id: 사용자가 오송·궁평2 또는 대전 사건 연도·시설을 명시하면 해당 저장 사례. region: 사용자가 쓴 시도(사건을 특정하지 않으면 해당 시도, 없으면 전체 사례).",
         "사례별 출처가 있는 통제·유입 기준, 시각 정밀도, 공식 특보·시설 규칙 신호, 같은 지역 신호 수, 검토에 필요한 추가 증거.",
         "완전한 PERC, 통제 원인·대응 성패·피해·복구·취약성 평가, 저장 자료 밖의 사실."),
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
_GROUP_WORDS = [("지하차도", "underpass"), ("하천변", "riverside"), ("둔치", "riverside"), ("고수부지", "riverside"), ("하상도로", "riverside"),
                ("출입구", "riverside"), ("천변", "riverside")]
_DRIVER_WORDS = [("내수형", "pluvial"), ("하천형", "river")]
_POST_EVENT_CASE_ALIASES = {
    "osong-2023": ("오송", "궁평2"),
    "daejeon-2020-07-30": ("대전 2020", "대전2020", "2020-07-30", "만년지하차도"),
    "daejeon-2023-07-14": ("대전 2023", "대전2023", "2023-07-14", "하상도로", "하상주차장"),
    "daejeon-2024-07-10": ("대전 2024", "대전2024", "2024-07-10", "오량", "갑천"),
}
_FACILITY_WORD = re.compile(r"시설|지하차도|하천변|둔치|고수부지|하상도로|출입구|천변")
_RAIN = re.compile(r"강우|호우|폭우|소나기|빗줄기|비\s*(?:가|는|도)?\s*(?:많이|오|와|내리|온|쏟|퍼붓)")
_OVERVIEW = re.compile(r"몇\s*곳|현황|전체|전국|몇\s*개")
_STATUS = re.compile(r"단계|수위|남았|상태|여유|얼마")
_OFFICIAL = re.compile(r"특보|홍수경보|홍수주의보|발령")
_VALIDATE = re.compile(r"검증|사례|실제\s*통제|통제\s*(?:시각|보다)|빨랐|늦었")
_POST_EVENT_REVIEW = re.compile(r"사후\s*(?:검토|분석|보고서|평가|리뷰)|사건\s*(?:복기|사후\s*검토)|재난\s*(?:복기|사후\s*분석)|PERC", re.IGNORECASE)


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


def _written_group(message: str) -> str | None:
    for word, group in _GROUP_WORDS:
        if word in message:
            return group
    return None


def _written_driver(message: str) -> str | None:
    for word, driver in _DRIVER_WORDS:
        if word in message:
            return driver
    return None


def _written_review_case_id(message: str) -> str | None:
    matches = [case_id for case_id, aliases in _POST_EVENT_CASE_ALIASES.items()
               if case_id in message or any(alias in message for alias in aliases)]
    return matches[0] if len(matches) == 1 else None


def _written_limit(message: str) -> int | None:
    match = re.search(r"(\d{1,2})\s*(?:곳|개|군데|위)", message)
    return int(match.group(1)) if match else None


def hints(message: str) -> list[dict[str, Any]]:
    region = nw.match_region(message)
    station = nw.find_station(message)
    facility = nw.find_facility(message)
    stage = _written_stage(message)
    driver = _written_driver(message)
    review_case_id = _written_review_case_id(message)
    out: list[dict[str, Any]] = []

    def add(name: str, **params: Any) -> None:
        out.append({"tool_name": name, "parameters": {k: v for k, v in params.items() if v is not None}})

    if _POST_EVENT_REVIEW.search(message):
        add("post_event_review", case_id=review_case_id, region=region if not review_case_id else None)
    elif _SCORE.search(message) and facility and facility["tier"] == "operational":
        add("rule_scorecard", facility=facility["name"])
    elif _VALIDATE.search(message):
        add("validation_cases", region=region)
    elif _OFFICIAL.search(message) and not station and not facility:
        add("get_official_forecasts", region=region)
    elif driver and not facility and (_RANK.search(message) or _RAIN.search(message) or "먼저" in message):
        add("rank_facilities", region=region, group=_written_group(message), driver=driver, limit=_written_limit(message))
    elif _FACILITY_WORD.search(message) and not facility and (_RANK.search(message) or _OVERVIEW.search(message) or "먼저" in message):
        add("rank_facilities", region=region, group=_written_group(message), limit=_written_limit(message))
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
    if params.get("group") is not None:
        group = params["group"] if params["group"] in ("underpass", "riverside") else _written_group(str(params["group"]))
        if group is None or group != _written_group(supplied):
            raise ValueError("The facility kind must be one the user wrote (지하차도 or 하천변).")
        clean["group"] = group
    if params.get("driver") is not None:
        driver = params["driver"] if params["driver"] in ("river", "pluvial") else _written_driver(str(params["driver"]))
        if driver is None or driver != _written_driver(supplied):
            raise ValueError("The facility risk type must be one the user named (하천형 or 내수형).")
        clean["driver"] = driver
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
    if params.get("case_id") is not None:
        case_id = str(params["case_id"])
        aliases = _POST_EVENT_CASE_ALIASES.get(case_id)
        if aliases is None or (case_id not in supplied and not any(alias in supplied for alias in aliases)):
            raise ValueError("The case must be one the user named (Osong 2023 or a named Daejeon case).")
        clean["case_id"] = case_id
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


def _review_signal(signal: dict[str, Any], precision: str) -> dict[str, Any]:
    at = signal.get("at")
    lead = signal.get("lead_min")
    if at is None:
        comparison = "저장된 재생 구간에서 이 신호가 확인되지 않음"
    elif signal.get("lead_is_lower_bound"):
        comparison = "재생 시작 전부터 신호가 있어 선행 분은 하한"
    elif precision == "upper_bound":
        if lead is not None and lead >= 0:
            comparison = f"보도 시각보다 {lead}분 먼저 관측됐으나 실제 통제와의 간격은 확인 불가"
        else:
            comparison = f"보도 시각보다 {abs(lead or 0)}분 뒤 관측; 보도 시점에는 이미 통제 중이어서 실제 통제 대비 지연은 확정할 수 없음"
    elif precision == "approximate":
        if lead is None:
            comparison = "근사 기준 시각과 비교할 수 없음"
        else:
            comparison = f"보도의 근사 시각 기준 약 {abs(lead)}분 {'전' if lead >= 0 else '후'}"
    elif lead is None:
        comparison = "기준 시각과 비교할 수 없음"
    else:
        comparison = f"분 단위 기준 시각보다 {abs(lead)}분 {'전' if lead >= 0 else '후'}"
    reviewed = {key: signal.get(key) for key in ("signal", "at", "lead_min", "lead_is_lower_bound", "source", "facility_id", "first_facility", "driver", "why")}
    reviewed["source_basis"] = signal.get("source") or "저장된 facility_risk 재생 (상단 rule 참조)"
    reviewed["comparison"] = comparison
    return reviewed


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
    # Agent answers in replay context must keep rainfall aligned to the selected observation time.
    # The visual board opts into current rainfall explicitly via its separate rain_mode=live query.
    rain_mode = "replay" if at else None
    region = getattr(request, "region", None)
    min_stage = getattr(request, "min_stage", None)
    if name == "get_watch_overview":
        data = nw.overview(at, region, min_stage, limit=10, rain_mode=rain_mode)
        return {"mode": data["mode"], "at": data["at"], "observed_at": data["observed_at"], "source": data["source"], "filter": data["filter"],
                "stations_total": data["stations_total"], "stations_observed": data["stations_observed"],
                "counts": data["counts"], "rain": data["rain"], "regions": data["regions"], "top": [_station_brief(row) for row in data["stations"][:10]],
                "view": _view(region=region, min_stage=min_stage),
                "coverage_note": "NATIONAL_WATCH: gauge stages against each station's official levels; facility links are watch-tier.",
                "limitations": data["limitations"]}
    if name == "rank_priority":
        limit = getattr(request, "limit", None) or 5
        data = nw.overview(at, region, None, limit=limit, rain_mode=rain_mode)
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
        detail = nw.station_detail(getattr(request, "station"), at, rain_mode=rain_mode)
        return {**_station_brief(detail), "mode": detail["mode"], "at": detail["at"], "recent": detail["recent"][-7:],
                "view": _view(station=detail),
                "coverage_note": "HISTORICAL_REPLAY: stored hourly observations." if detail["mode"] == "replay" else "LIVE_OBSERVATION: check observation age before interpretation.",
                "limitations": ["단계는 관측소 공식 기준 수위 기준이며 시설 침수심이 아니다.", BASELINE_CAVEAT, WATCH_CAVEAT]}
    if name == "navigate_board":
        station = None
        facility = None
        if getattr(request, "facility", None):
            facility = nw.facility_index()[request.facility]
            station = nw.station_detail(facility["station_code"], at, rain_mode=rain_mode) if facility["station_code"] else None
        elif getattr(request, "station", None):
            station = nw.station_detail(request.station, at, rain_mode=rain_mode)
        scope = region or (station["region"] if station else facility["region"] if facility else None)
        data = nw.overview(at, scope, min_stage, limit=5, rain_mode=rain_mode) if not station else None
        result: dict[str, Any] = {"view": _view(region=region, station=station, facility=facility, min_stage=min_stage), "mode": (station or data)["mode"],
                                  "moved_to": facility["name"] if facility else station["name"] if station else region or nw.STAGE_KO.get(min_stage or "", "전국"),
                                  "coverage_note": "NAVIGATION: the board follows this view; numbers describe the destination only.",
                                  "limitations": [WATCH_CAVEAT if (facility or station) else "지역 이동은 화면 범위만 바꾼다."]}
        if station:
            result["station"] = _station_brief(station)
        if facility:
            result["facility"] = {key: facility.get(key) for key in ("facility_id", "name", "kind_ko", "tier", "distance_km", "region", "sgg", "event_id", "river_name")}
            if not facility["station_code"]:
                result["facility"]["note"] = "5 km 안에 하천 관측소가 없어 단계를 매기지 않는 시설(강우만)."
        if data:
            result["counts"] = data["counts"]
            result["top"] = [_station_brief(row) for row in data["stations"][:5]]
        return result
    if name == "draft_situation_report":
        data = nw.overview(at, region, None, limit=5, rain_mode=rain_mode)
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
    if name == "rank_facilities":
        limit = getattr(request, "limit", None) or 5
        group = getattr(request, "group", None)
        driver = getattr(request, "driver", None)
        from . import facility_risk
        data = facility_risk.facility_risk(at, region, driver, limit=2000, rain_mode=rain_mode)
        facilities = [row for row in data["facilities"] if not group or row["group"] == group]
        by_level = {label: sum(1 for row in facilities if row["level_label"] == label) for label in facility_risk.LEVELS.values()}
        counts = {"total": len(facilities), "by_driver": {key: sum(1 for row in facilities if row["driver"] == key) for key in ("river", "pluvial")},
                  "by_level": by_level, "attention_or_above": sum(row["level"] >= 1 for row in facilities),
                  "advisory_or_above": sum(row["level"] >= 2 for row in facilities),
                  "warning_or_above": sum(row["level"] >= 3 for row in facilities),
                  "under_heavy_rain": sum(((row.get("rain") or {}).get("rain_12h_mm") or 0) >= 110
                                           or ((row.get("rain") or {}).get("rain_3h_mm") or 0) >= 60
                                           or (row.get("rain") or {}).get("rain_12h_mm") is None and (row.get("rain") or {}).get("rain_3h_mm") is None
                                           and ((row.get("rain") or {}).get("rain_1h_mm") or 0) >= 15
                                           for row in facilities)}
        selected = facilities[:limit]
        keys = ("facility_id", "name", "kind_ko", "group", "tier", "region", "driver", "driver_reason", "level", "level_label", "why",
                "gauge", "distance_km", "stage", "minutes_to_planned_flood", "rain")
        ranked = [{"rank": index + 1, **{key: row.get(key) for key in keys}} for index, row in enumerate(selected)]
        top = selected[0] if selected else None
        view_facility = {**top, "station_code": None} if top and not region else None
        return {"mode": data["mode"], "at": data["at"], "rain_at": data["rain_at"], "region": region or "전국",
                "group": nw.GROUP_KO.get(group or "", "전체 시설"), "driver": driver, "limit": limit,
                "counts": counts, "ranked": ranked,
                "view": _view(region=region, facility=view_facility, layer="rain" if driver == "pluvial" else None) if view_facility else _view(region=region, layer="rain" if driver == "pluvial" else None),
                "coverage_note": "FACILITY_RISK: ordered by 0–4 risk level using the facility's flooding driver: river stage or nearby rain.",
                "limitations": data["limitations"]}
    if name == "get_official_forecasts":
        from . import flood_forecast
        data = flood_forecast.summary(at)
        catalogue = nw.stations()
        active = [{**row, "region": catalogue[row["station_code"]].region if row["station_code"] in catalogue else None} for row in data["active"]]
        if region:
            active = [row for row in active if row["region"] == region]
        return {"mode": data["mode"], "at": data["at"], "region": region or "전국", "error": data["error"],
                "counts": {"warning": sum(1 for row in active if row["level"] == "warning"), "advisory": sum(1 for row in active if row["level"] == "advisory")},
                "active": active[:10], "active_total": len(active), "source": data["source"], "view": _view(region=region),
                "coverage_note": "OFFICIAL_FORECAST: HRFCO 홍수예보 발령 as issued; FloodOps does not alter it.",
                "limitations": data["limitations"]}
    if name == "validation_cases":
        from . import case_validation
        data = case_validation.scorecard()
        cases = [item for item in data["cases"] if not region or nw.match_region(item["region"]) == region]
        return {"region": region or "전체", "built_at": data["built_at"], "rule": data["rule"], "cases": cases, "view": _view(region=region),
                "coverage_note": "VALIDATION_REPLAY: stored replay of facility_risk every 10 minutes against reported control times.",
                "limitations": data["limitations"]}
    if name == "post_event_review":
        from . import case_validation
        data = case_validation.scorecard()
        case_id = getattr(request, "case_id", None)
        cases = [item for item in data["cases"]
                 if (not case_id or item["id"] == case_id) and (not region or nw.match_region(item["region"]) == region)]
        reviewed = []
        for item in cases:
            reference = item["reference"]
            regional = item.get("region_at_reference") or {}
            reviewed.append({
                "id": item["id"], "title": item["title"], "region": item["region"],
                "reference": reference,
                "signals": [_review_signal(signal, reference["precision"]) for signal in item["signals"]],
                "regional_context_at_reference": regional,
                "regional_context_note": (f"재생 기준 시각 주변 {regional.get('at')}에 같은 지역 시설 "
                                          f"{regional.get('total', 0)}곳 중 주의 이상 {regional.get('advisory_or_above', 0)}곳, "
                                          f"경계 이상 {regional.get('warning_or_above', 0)}곳이었다. 이 수치는 신호의 원인이나 선별력을 입증하지 않는다."),
            })
        return {
            "document_type": "PERC-inspired evidence-limited desk review",
            "region": region or (reviewed[0]["region"] if case_id and reviewed else "전체 사례"), "case_id": case_id,
            "scorecard_built_at": data["built_at"],
            "replay_step_min": data["step_min"], "rule": data["rule"], "cases": reviewed,
            "review_lenses": {
                "event_reference": "사건별 통제 또는 유입 기준과 출처·시각 정밀도를 기록한다.",
                "warning_and_facility_signals": "저장된 공식 홍수특보 이력과 시설 위험 규칙 재생 시각을 비교한다.",
                "regional_context": "기준 시각 주변의 같은 지역 시설 신호 수를 함께 본다.",
                "response_recovery_and_causality": "자료가 없어 평가하지 않는다.",
            },
            "evidence_to_collect": [
                "시설별 실제 통제·해제 시각, 결정자, 판단 근거와 전달 기록",
                "현장 강우·수위 원자료와 시설별 배수·유입 경로 및 점검 기록",
                "경보 수신·전파·대응 기록과 관계기관 조정 기록",
                "피해·대피·구조·복구 기록, 현장 관계자 면담과 취약성 정보",
            ],
            "view": _view(region=region),
            "coverage_note": "PERC-inspired desk review of stored event scorecards; this is not a full PERC and makes no causal finding.",
            "limitations": [*data["limitations"],
                            "현재 자료는 사건 기준·공식 특보·시설 위험 규칙 재생에 한정된다. 인터뷰, 취약성, 대응 과정, 피해·복구 자료가 없어 전체 재난관리 성과를 평가하지 않는다.",
                            "기준 시각이 보도상 근사 또는 상한이면 표시된 선행·지연은 실제 통제 시각과 같지 않을 수 있다."],
        }
    if name == "get_rain_status":
        limit = getattr(request, "limit", None) or 5
        data = nw.overview(at, region, None, limit=2000, rain_mode=rain_mode)
        rain = data["rain"]
        rained_on = [row for row in data["stations"] if ((row.get("rain_nearby") or {}).get("intensity_mm_h") or 0) >= nw.RAIN_CLASSES[1][0]]
        return {"mode": rain["mode"], "at": data["at"], "observed_at": rain["observed_at"], "region": region or "전국", "available": rain["available"],
                "error": rain["error"], "basis": rain["basis"], "gauges_reporting": rain["gauges_reporting"], "raining": rain["raining"], "heavy_or_above": rain["heavy_or_above"],
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
            if (result.get("facility") or {}).get("note"):
                text += " " + result["facility"]["note"]
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
        elif name == "rank_facilities":
            rows = result.get("ranked", [])
            counts = result.get("counts", {})
            text = (f"{result.get('region')} {result.get('group')} {counts.get('total', 0)}곳 중 관심 이상 {counts.get('attention_or_above', 0)}곳, "
                    f"주의 이상 {counts.get('advisory_or_above', 0)}곳, 경계 이상 {counts.get('warning_or_above', 0)}곳입니다.")
            if rows:
                parts = []
                for row in rows:
                    driver_label = "하천형" if row.get("driver") == "river" else "내수형"
                    bit = f"{row['rank']}위 {row['name']}({row['kind_ko']}, {driver_label}, {row['region']}) {row['level_label']} · {row['why']}"
                    if row.get("gauge"):
                        bit += f" · {row['gauge']} {row.get('distance_km')} km"
                    if row.get("minutes_to_planned_flood") is not None:
                        bit += f" · 계획홍수위까지 {row['minutes_to_planned_flood']}분"
                    rain = row.get("rain") or {}
                    rain_amounts = [(label, rain.get(key)) for label, key in (("12시간", "rain_12h_mm"), ("3시간", "rain_3h_mm"), ("1시간", "rain_1h_mm"))
                                    if rain.get(key) is not None]
                    if rain_amounts:
                        bit += " · 주변 강우 " + " · ".join(f"{label} {amount:.1f} mm" for label, amount in rain_amounts)
                        if rain.get("name"):
                            bit += f"({rain['name']} {rain.get('distance_km')} km)"
                    parts.append(bit)
                text += " " + "; ".join(parts) + "."
        elif name == "get_official_forecasts":
            counts = result.get("counts", {})
            if result.get("error") and not result.get("active_total"):
                text = "공식 홍수특보 피드를 읽지 못했습니다."
            else:
                text = (f"{(result.get('at') or '')[:16].replace('T', ' ')} 기준 {result.get('region')} 공식 홍수경보 {counts.get('warning', 0)}곳, "
                        f"홍수주의보 {counts.get('advisory', 0)}곳입니다.")
                rows = result.get("active") or []
                if rows:
                    text += " " + "; ".join(
                        f"{row['station_name']} {row['level_ko']}(발령 {row['issued_at'][5:16].replace('T', ' ')}"
                        + (f", 예상 {row['forecast_time'][11:16]} {row['forecast_level_m']:.2f} m" if row.get("forecast_time") and row.get("forecast_level_m") is not None else "")
                        + ")" for row in rows[:5]) + "."
        elif name == "post_event_review":
            parts = []
            for item in result.get("cases", []):
                ref = item["reference"]
                signals = item.get("signals", [])
                selected = [signal for signal in signals if signal.get("signal", "").startswith("공식 홍수")
                            or "시설 중 첫" in signal.get("signal", "")]
                timing = "; ".join(
                    f"{signal['signal']} {signal['at'][11:16] if signal.get('at') else '없음'} ({signal['comparison']})"
                    for signal in selected
                )
                regional = item.get("regional_context_at_reference") or {}
                parts.append(f"{item['title']}: 기준 {ref['label']} [{ref['precision_ko']}]; {timing}; "
                             f"기준 시각 주변 같은 지역 시설 {regional.get('total', 0)}곳 중 주의 이상 "
                             f"{regional.get('advisory_or_above', 0)}곳, 경계 이상 {regional.get('warning_or_above', 0)}곳")
            text = ("저장 사례 기반 PERC 참고형 사후 검토 초안입니다. " + " / ".join(parts)
                    + ". 통제 사유·대응 성패·피해·복구는 현재 자료로 평가하지 않았습니다.") if parts else "선택 지역의 저장 사후 검토 사례가 없습니다."
        elif name == "validation_cases":
            parts = []
            for item in result.get("cases", []):
                ref = item["reference"]
                picks = [s for s in item["signals"] if s["signal"] in ("공식 홍수주의보", "공식 홍수경보") or s["signal"].endswith("첫 주의 이상")]
                region_now = item.get("region_at_reference") or {}
                parts.append(f"{item['title']}: 기준 {ref['label']} — "
                             + ", ".join(f"{s['signal']} {s['at'][11:16] if s['at'] else '없음'}({s['verdict']})" for s in picks)
                             + f"; 기준 시각에 {item['region']} 시설 {region_now.get('total', 0)}곳 중 주의 이상 {region_now.get('advisory_or_above', 0)}곳")
            text = " / ".join(parts) + ". 통제 시각은 보도 기준입니다." if parts else "이 지역의 검증 사례가 없습니다."
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

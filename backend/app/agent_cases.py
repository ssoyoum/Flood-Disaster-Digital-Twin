"""Agent tools for the cases beyond Osong: Seoul 2022, Pohang 2022, Andong-Uiseong 2026.

Osong keeps its own catalogue in ``agent_tools``. This module adds, per event, the tools that wrap the
counterfactual endpoints already exposed to the UI, the rules that keep model-supplied values tied to the
user's words, and the starter questions. Every number still comes from the deterministic repositories.
"""

from __future__ import annotations

import re
from typing import Any

from .seoul_repository import (
    DESIGN_RAINFALL_MM_PER_HOUR,
    DORIMCHEON_TUNNEL_STORAGE_M3,
    SEOUL_EVENT_ID,
    analyze_alert_timing,
    analyze_storage_capture,
    get_seoul_reconstruction,
)
from .timeline_cases import CASES as TIMELINE_CASES, analyze_response_timing, get_timeline_reconstruction, is_timeline_case

SINWOL_STORAGE_M3 = 320_000
PRESS_NOTE = "PRESS_REPORT: incident times other than gauge thresholds are press-reported values, not official source pages."

_COMMON_TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "get_event",
        "description": "Get the registered flood event and its current data status.",
        "input_fields": ["event_id"],
        "output": "registered event metadata",
        "use_when": "사건 이름·위치·자료 상태를 물을 때.",
        "parameters": "event_id만 쓴다.",
        "can_say": "사건명, 위치, 사건 흐름, 자료 연결 상태.",
        "cannot_say": "시각별 수치나 분석 결과.",
        "examples": ["이 사건 뭐야?"],
    },
    {
        "name": "get_reconstruction",
        "description": "Get the reconstructed incident timeline, interventions, and provenance for this event.",
        "input_fields": ["event_id"],
        "output": "incident timeline with source and confidence per stage",
        "use_when": "몇 시에 무슨 일이 있었는지, 사건 경과, 가정 질문의 기준이 되는 실제 시각이 필요할 때.",
        "parameters": "event_id만 쓴다.",
        "can_say": "단계별 시각·이름·출처·확신도(관측 또는 언론 보도), 등록된 반사실 질문 목록.",
        "cannot_say": "시각을 바꿨을 때의 결과(분석 도구를 쓴다), 사망자·피해액.",
        "examples": ["그날 경과를 시간순으로 알려줘"],
    },
)

_SEOUL_TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "get_observation_summary",
        "description": "Get Seoul rain-gauge peaks and the official flood-trace exposure counts for the Dorimcheon corridor.",
        "input_fields": ["event_id"],
        "output": "observed rainfall peaks and official flood-trace overlay counts",
        "use_when": "비가 얼마나 왔는지, 침수흔적·흔적과 겹친 건물·도로가 얼마인지 물을 때.",
        "parameters": "event_id만 쓴다.",
        "can_say": "강우계별 최대 60분 강우·시각·8/8 합계, 침수흔적 수·면적·침수심 통계, 흔적과 겹친 건축물 수, 흔적 안 도로 길이.",
        "cannot_say": "흔적이 언제 생겼는지(시각 없음), 사상자, 피해액.",
        "examples": ["신림 강우계 최대 강우는 얼마였어?", "침수흔적과 겹친 건물은 몇 동이야?"],
    },
    {
        "name": "analyze_alert_timing",
        "description": "Alert lead time before the first Sillim rescue call (20:59) when a low-lying alert is sent at a rain threshold or a fixed time.",
        "input_fields": ["event_id", "thresholds_mm_per_hour", "alert_times"],
        "output": "alert time per assumption, minutes before the first rescue call and earlier than the actual 21:19 alert",
        "use_when": "강우가 시간당 N mm를 넘을 때 경보·문자를 보냈다면, 또는 HH:MM에 저지대 경보를 보냈다면 첫 구조 신고까지 몇 분이었는지 물을 때.",
        "parameters": "thresholds_mm_per_hour: 사용자가 쓴 시간당 mm 값. alert_times: 사용자가 쓴 HH:MM이나 사건 단계 시각. 둘 중 하나 이상.",
        "can_say": "경보 시각, 첫 구조 신고(20:59)까지 남은 분, 실제 첫 문자(21:19)보다 빠른 분.",
        "cannot_say": "대피 인원, 인명 피해 감소.",
        "examples": ["시간당 95mm 넘었을 때 문자를 보냈다면?", "12:50 호우경보 때 바로 저지대 경보를 냈다면?"],
    },
    {
        "name": "analyze_storage_capture",
        "description": "Rain volume above the drainage capacity at a Seoul gauge and how much an assumed storage tunnel could hold, with the time it fills.",
        "input_fields": ["event_id", "storage_m3", "capacity_mm_per_hour", "runoff_coefficient"],
        "output": "excess volume, captured share, storage-full time; volume arithmetic only",
        "use_when": "빗물터널·저류시설이 있었다면 얼마나 담았을지, 언제 가득 찼을지 물을 때.",
        "parameters": "storage_m3: 사용자가 쓴 값 또는 등록값(도림천 터널 400000, 신월 320000). capacity_mm_per_hour: 사용자가 쓴 값 또는 95/100/110. runoff_coefficient: 사용자가 쓴 0~1 값. 쓰지 않으면 생략한다.",
        "can_say": "처리 능력 초과 강우 부피, 저류 비율, 가득 차는 시각과 첫 구조 신고까지 남은 분.",
        "cannot_say": "침수 면적·침수심 감소, 피해 감소. 면적은 도림천 유역 40.96 km2(문헌값)이고 신림P 강우를 유역 전체에 같게 적용한다.",
        "examples": ["도림천 빗물터널이 있었다면 얼마나 담았을까?", "신월 규모 저류시설이면?"],
    },
)


def _timeline_tool(event_id: str) -> dict[str, Any]:
    case = TIMELINE_CASES[event_id]
    choices = "; ".join(f"{item['id']} = {item['name']} (실제 {item['actual_time'][11:16]})" for item in case["interventions"])
    return {
        "name": "analyze_response_timing",
        "description": "Move one registered response action to other clock times and count the minutes before the reported milestones that followed.",
        "input_fields": ["event_id", "intervention_id", "action_times"],
        "output": "minutes before each milestone and earlier than the actual action; time arithmetic only",
        "use_when": "대응(진입 금지 안내, 대피명령, 산사태 경보 상향 등)을 몇 시에 했다면, N분 일찍 했다면 어땠는지 물을 때.",
        "parameters": f"intervention_id: {choices}. action_times: 사용자가 쓴 HH:MM이나 사건 단계 시각, 최대 10개.",
        "can_say": "가정한 대응 시각이 이후 사건보다 몇 분 앞서는지, 실제보다 몇 분 빠른지.",
        "cannot_say": "대피 성공, 인명·피해 감소. 사건 시각은 언론 보도 기준이다.",
        "examples": [example["question"] for example in _TIMELINE_EXAMPLES[event_id]],
    }


_TIMELINE_FACTS_TOOL = {
    "name": "get_observation_summary",
    "description": "Get the press-reported facts registered for this event (damage counts, rainfall totals, follow-up measures) with sources.",
    "input_fields": ["event_id"],
    "output": "reported facts with source, not model output",
    "use_when": "비가 얼마나 왔는지, 피해·대피 규모, 사후 조치를 물을 때.",
    "parameters": "event_id만 쓴다.",
    "can_say": "등록된 보도 수치와 출처.",
    "cannot_say": "보도에 없는 수치, 계산된 피해.",
    "examples": ["대피 인원은 얼마였어?"],
}

_SEOUL_EXAMPLES: tuple[dict[str, str], ...] = (
    {"workflow": "alert_timing", "label": "95mm 경보", "question": "신림 강우계가 시간당 95mm를 넘었을 때 저지대 경보를 보냈다면 첫 구조 신고까지 몇 분이었나요?"},
    {"workflow": "storage_capture", "label": "빗물터널", "question": "도림천 빗물터널(40만 m³)이 있었다면 처리 능력을 넘은 비를 얼마나 담았을까요?"},
    {"workflow": "observation", "label": "흔적 노출", "question": "공식 침수흔적과 겹친 건물은 몇 동인가요?"},
    {"workflow": "situation", "label": "상황 타임라인", "question": "서울 도림천 침수 상황을 타임라인으로 보여주세요."},
)

_TIMELINE_EXAMPLES: dict[str, tuple[dict[str, str], ...]] = {
    "pohang-2022": (
        {"workflow": "response_timing", "label": "06:00 진입 금지", "question": "06:00에 지하주차장 진입 금지 안내를 했다면 침수 시작까지 몇 분 있었나요?"},
        {"workflow": "response_timing", "label": "30분 일찍 안내", "question": "진입 금지 안내를 30분 일찍 했다면 완전 침수까지 몇 분 남나요?"},
        {"workflow": "observation", "label": "보도 수치", "question": "지하주차장에 들어온 물은 얼마로 보도됐나요?"},
        {"workflow": "situation", "label": "상황 타임라인", "question": "포항 냉천 침수 상황을 타임라인으로 보여주세요."},
    ),
    "andong-uiseong-2026": (
        {"workflow": "response_timing", "label": "23:40 대피명령", "question": "23:40 홍수경보 때 바로 대피명령을 냈다면 경보 수위 도달 예측까지 몇 분이었나요?"},
        {"workflow": "response_timing", "label": "산사태 경보 00:00", "question": "산사태 위기경보를 00:00에 올렸다면 실제보다 얼마나 빨랐나요?"},
        {"workflow": "observation", "label": "대피 규모", "question": "대피 인원과 침수된 임시주택은 몇 동으로 보도됐나요?"},
        {"workflow": "situation", "label": "상황 타임라인", "question": "안동·의성 침수 상황을 타임라인으로 보여주세요."},
    ),
}

CASE_TOOL_PARAMETERS: dict[str, set[str]] = {
    "analyze_alert_timing": {"thresholds_mm_per_hour", "alert_times"},
    "analyze_storage_capture": {"storage_m3", "capacity_mm_per_hour", "runoff_coefficient"},
    "analyze_response_timing": {"intervention_id", "action_times"},
}


def handles(event_id: str) -> bool:
    return event_id == SEOUL_EVENT_ID or is_timeline_case(event_id)


def tools_for(event_id: str) -> list[dict[str, Any]]:
    if event_id == SEOUL_EVENT_ID:
        return [dict(tool) for tool in (*_COMMON_TOOLS, *_SEOUL_TOOLS)]
    return [dict(tool) for tool in (*_COMMON_TOOLS, _TIMELINE_FACTS_TOOL, _timeline_tool(event_id))]


def examples_for(event_id: str) -> list[dict[str, str]]:
    source = _SEOUL_EXAMPLES if event_id == SEOUL_EVENT_ID else _TIMELINE_EXAMPLES[event_id]
    return [dict(example) for example in source]


def reconstruction(event_id: str) -> dict[str, Any]:
    result = get_seoul_reconstruction() if event_id == SEOUL_EVENT_ID else get_timeline_reconstruction(event_id)
    # The timeline tool output is what the model reads; drop the long gauge series it cannot cite usefully.
    compact = {key: value for key, value in result.items() if key != "rainfall_series"}
    return {**compact, "coverage_status": "fallback", "coverage_note": PRESS_NOTE}


def observation_summary(event_id: str) -> dict[str, Any]:
    if event_id == SEOUL_EVENT_ID:
        result = get_seoul_reconstruction()
        return {
            "rainfall_peaks": result["rainfall_peaks"],
            "design_rainfall_mm_per_hour": result["design_rainfall_mm_per_hour"],
            "exposure": result["exposure"],
            "coverage_status": "covered",
            "coverage_note": "Seoul 10-minute rain gauges and the official 2022 flood traces; buildings from a 2026-08-09 register filtered to approvals on or before 2022-08-08.",
        }
    return {
        "reported_facts": TIMELINE_CASES[event_id]["reported_facts"],
        "coverage_status": "fallback",
        "coverage_note": "Press-reported values listed with their sources; no gauge series or flood extent is connected.",
    }


def run_tool(tool_name: str, event_id: str, request: Any) -> dict[str, Any]:
    if tool_name == "analyze_alert_timing":
        result = analyze_alert_timing(thresholds_mm_per_hour=request.thresholds_mm_per_hour or [], alert_times=request.alert_times or [])
    elif tool_name == "analyze_storage_capture":
        result = analyze_storage_capture(
            storage_m3=request.storage_m3 or DORIMCHEON_TUNNEL_STORAGE_M3,
            capacity_mm_per_hour=request.capacity_mm_per_hour or DESIGN_RAINFALL_MM_PER_HOUR,
            runoff_coefficient=request.runoff_coefficient or 1.0,
        )
        # The full 10-minute excess trace is not needed to answer; keep the result short for the model.
        result = {key: value for key, value in result.items() if key != "excess_timeline"}
    elif tool_name == "analyze_response_timing":
        result = analyze_response_timing(event_id, request.intervention_id or "", request.action_times or [])
    else:
        raise KeyError(f"Unknown agent tool: {tool_name}")
    return {**result, "coverage_status": "fallback", "coverage_note": PRESS_NOTE}


# ── value checks: everything a model passes must be traceable to the user's words or a registered value ──

_MM_VALUE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d)?)\s*(?:mm|밀리)", re.IGNORECASE)
_DECIMAL = re.compile(r"(?<![\d.])(0(?:\.\d+)?|1(?:\.0+)?)(?![\d.])")


def written_mm(text: str) -> list[float]:
    return [float(value) for value in _MM_VALUE.findall(text)]


def written_volumes(text: str) -> list[float]:
    values: list[float] = []
    for number, unit in re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(만)?\s*(?:m³|m3|톤|t\b|세제곱)", text):
        values.append(float(number) * (10_000 if unit else 1))
    for number in re.findall(r"(?<![\d.])(\d{5,7})(?![\d.])", text.replace(",", "")):
        values.append(float(number))
    return values


def validate(tool_name: str, event_id: str, params: dict[str, Any], supplied: str, user_clocks: set[str], milestone_clocks: set[str], relative_clocks: list[str]) -> None:
    """Raise ValueError unless every parameter is the user's own value or a registered one."""

    allowed_tools = {tool["name"] for tool in tools_for(event_id)}
    if tool_name not in allowed_tools:
        raise ValueError(f"{tool_name} is not registered for {event_id}.")
    clocks = user_clocks | milestone_clocks | set(relative_clocks)
    if tool_name == "analyze_alert_timing":
        thresholds = params.get("thresholds_mm_per_hour") or []
        times = params.get("alert_times") or []
        if not thresholds and not times:
            raise ValueError("Alert timing needs a rainfall threshold or an alert time from the question.")
        if not all(isinstance(value, (int, float)) and float(value) in written_mm(supplied) for value in thresholds):
            raise ValueError("Rainfall thresholds must be mm values written in the question.")
        if not all(isinstance(value, str) and value in clocks for value in times):
            raise ValueError("Alert times must appear in the question or be a recorded milestone time.")
    elif tool_name == "analyze_storage_capture":
        storage = params.get("storage_m3")
        if storage is not None and float(storage) not in {DORIMCHEON_TUNNEL_STORAGE_M3, SINWOL_STORAGE_M3, *written_volumes(supplied)}:
            raise ValueError("Storage volume must be written in the question or a registered tunnel volume.")
        capacity = params.get("capacity_mm_per_hour")
        if capacity is not None and float(capacity) not in {95.0, 100.0, 110.0, *written_mm(supplied)}:
            raise ValueError("Drainage capacity must be written in the question or a registered design rainfall.")
        runoff = params.get("runoff_coefficient")
        if runoff is not None and float(runoff) not in {float(value) for value in _DECIMAL.findall(supplied)}:
            raise ValueError("Runoff coefficient must be written in the question.")
    elif tool_name == "analyze_response_timing":
        registered = {item["id"] for item in TIMELINE_CASES[event_id]["interventions"]}
        if params.get("intervention_id") not in registered:
            raise ValueError(f"intervention_id must be one of: {', '.join(sorted(registered))}.")
        times = params.get("action_times") or []
        if not times or len(times) > 10 or not all(isinstance(value, str) and value in clocks for value in times):
            raise ValueError("Action times must appear in the question or be a recorded milestone time.")


# ── router hints: tools whose values the user literally wrote ──

_ALERT_WORDS = re.compile(r"경보|문자|알림|알렸|경고|alert", re.IGNORECASE)
_STORAGE_WORDS = re.compile(r"터널|저류|빗물|tunnel|storage", re.IGNORECASE)
_EARLIER = re.compile(r"(\d{1,3})\s*분\s*(?:더\s*)?(?:일찍|먼저|빨리|앞당|이르게|일러)")
_INTERVENTION_WORDS: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "pohang-2022": (("parking_entry_ban", re.compile(r"진입|금지|안내|방송|주차장|통제|막")),),
    "andong-uiseong-2026": (
        ("landslide_alert", re.compile(r"산사태|산림청")),
        ("evacuation_order", re.compile(r"대피|명령|피난")),
    ),
}


def intervention_for(event_id: str, message: str) -> dict[str, Any] | None:
    for intervention_id, pattern in _INTERVENTION_WORDS.get(event_id, ()):
        if pattern.search(message):
            return next(item for item in TIMELINE_CASES[event_id]["interventions"] if item["id"] == intervention_id)
    return None


def relative_clocks(event_id: str, message: str) -> list[str]:
    """Resolve "N분 일찍" against the actual time of the response the question names."""

    if not is_timeline_case(event_id):
        return []
    intervention = intervention_for(event_id, message)
    if intervention is None:
        return []
    hour, minute = int(intervention["actual_time"][11:13]), int(intervention["actual_time"][14:16])
    clocks = []
    for match in _EARLIER.finditer(message):
        total = (hour * 60 + minute - int(match.group(1))) % (24 * 60)
        clocks.append(f"{total // 60:02d}:{total % 60:02d}")
    return clocks


def hints(event_id: str, message: str, clocks: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if event_id == SEOUL_EVENT_ID:
        mm = [value for value in written_mm(message) if 0 < value <= 200]
        if _STORAGE_WORDS.search(message):
            params: dict[str, Any] = {}
            volumes = written_volumes(message)
            if volumes:
                params["storage_m3"] = volumes[0]
            elif "신월" in message:
                params["storage_m3"] = SINWOL_STORAGE_M3
            out.append({"tool_name": "analyze_storage_capture", "parameters": params})
        elif _ALERT_WORDS.search(message) and (mm or clocks):
            params = {}
            if mm:
                params["thresholds_mm_per_hour"] = mm
            if clocks:
                params["alert_times"] = clocks
            out.append({"tool_name": "analyze_alert_timing", "parameters": params})
        if re.search(r"비가|강우|강수|흔적|건물|도로|노출", message) and not out:
            out.append({"tool_name": "get_observation_summary", "parameters": {}})
        return out
    intervention = intervention_for(event_id, message)
    times = [*clocks, *relative_clocks(event_id, message)]
    if intervention and times:
        out.append({"tool_name": "analyze_response_timing", "parameters": {"intervention_id": intervention["id"], "action_times": times}})
    elif re.search(r"비가|강우|피해|대피 인원|대피는|보도|몇 동|규모", message):
        out.append({"tool_name": "get_observation_summary", "parameters": {}})
    return out

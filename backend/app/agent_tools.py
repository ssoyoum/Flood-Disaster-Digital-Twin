"""Registered, deterministic tools for the future FloodOps Agent.

The tool layer delegates to existing domain services and repositories. It does
not read GIS files directly, call external APIs, or infer missing measurements.
"""

from collections.abc import Callable
import re
from typing import Any

from . import agent_cases
from .data import get_event
from .hand_sensitivity import analyze_hand_threshold
from .osong_repository import get_osong_reconstruction, get_osong_summary
from .schemas import (
    AgentToolCallRequest,
    AgentIntentPlanRequest,
    AgentIntentPlanResult,
    AgentWorkflowRequest,
    ClosureTimingRequest,
    ClosureTimingResult,
    ExposureInventoryResult,
    InflowDelayRequest,
    InflowDelayResult,
    ScenarioComparisonResult,
)
from .services import (
    ReconstructionUnavailable,
    analyze_closure_timing,
    analyze_inflow_delay,
    build_exposure_inventory,
)


ToolHandler = Callable[[str, AgentToolCallRequest], dict[str, Any]]


# What each tool can and cannot answer, written for the model that picks tools.
# `name`, `input_fields` and `output` stay stable for the API; the Korean fields
# tell Gemini when a tool fits, what its inputs mean, and which claims it does not support.
_TOOL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "get_event",
        "description": "Get the registered flood event and its current data status.",
        "input_fields": ["event_id"],
        "output": "registered event metadata",
        "use_when": "사건 이름·위치·대상 시설·자료 상태를 물을 때, 또는 답의 맥락을 소개할 때.",
        "parameters": "event_id만 쓴다.",
        "can_say": "사건명, 위치, 대상 시설(궁평2지하차도), 사건 흐름 설명, 자료 연결 상태.",
        "cannot_say": "사건 시각별 수치나 분석 결과(다른 도구를 쓴다).",
        "examples": ["이 사건 뭐야?", "어떤 자료가 연결돼 있어?"],
    },
    {
        "name": "get_reconstruction",
        "description": "Get the connected historical reconstruction replay and provenance.",
        "input_fields": ["event_id"],
        "output": "historical reconstruction response",
        "use_when": "사건 경과·타임라인·몇 시에 무슨 일이 있었는지 물을 때, 가정 질문의 기준이 되는 실제 시각이 필요할 때.",
        "parameters": "event_id만 쓴다.",
        "can_say": "04:10 홍수경보, 06:40 계획홍수위 도달, 07:50 월류, 08:09 임시제방 붕괴, 08:27 지하차도 유입, 08:35 주행불능, 08:40 완전침수 같은 기록 시각과 기준 통제 시각(intervention.trigger_time, 08:27).",
        "cannot_say": "시각이 바뀌었을 때의 결과(통제·지연 도구를 쓴다), 피해 규모.",
        "examples": ["오송 사고 요약해줘", "제방은 몇 시에 무너졌어?", "그날 경과를 시간순으로 알려줘"],
    },
    {
        "name": "get_observation_summary",
        "description": "Get observed rainfall and river water-level peaks (value, time, station), observation period, and connected layer counts for the event.",
        "input_fields": ["event_id"],
        "output": "observed hydromet peaks and data counts, not a forecast",
        "use_when": "비가 얼마나 왔는지, 하천 수위가 얼마였는지, 관측 기록·자료 규모를 물을 때.",
        "parameters": "event_id만 쓴다.",
        "can_say": "최대 시간강우(mm/h)·시각·관측소, 최고 수위(m)·시각·관측소, 강우 기록 수, 건물·도로·하천 자료 수.",
        "cannot_say": "비가 덜 오거나 더 왔을 때의 결과(수문·수리모형 없음), 예보.",
        "examples": ["그날 비가 얼마나 왔어?", "미호강 수위는 최고 얼마였어?"],
    },
    {
        "name": "analyze_closure_timing",
        "description": "Compare hypothetical underpass closure times with observed reconstruction milestones.",
        "input_fields": ["event_id", "closure_times"],
        "output": "closure timing what-if result",
        "use_when": "지하차도를 몇 시에 통제·차단·폐쇄·막았다면, N분 일찍/늦게 막았다면, 경보 직후 통제했다면 어땠는지 물을 때.",
        "parameters": "closure_times: [\"HH:MM\", ...] 최대 10개. 사용자가 쓴 시각, 사건 단계 시각(get_reconstruction 결과), 또는 suggested_tools가 기준 통제 시각 08:27에서 계산해 준 상대 시각만 쓴다.",
        "can_say": "각 통제 시각이 유입·주행불능·완전침수보다 몇 분 앞서는지, 통제 시점의 사건 단계, 유입 전·후 통제 분류.",
        "cannot_say": "통제로 줄어든 차량 수·사상자·침수심. 결과는 신규 진입을 막았다는 가정의 시간 비교다.",
        "examples": ["08:10에 통제했다면 유입까지 몇 분 여유였어?", "차단을 10분 일찍 했다면?", "경보 나오자마자 막았으면?"],
    },
    {
        "name": "analyze_inflow_delay",
        "description": "Shift downstream reconstruction milestones by an explicit inflow-delay assumption.",
        "input_fields": ["event_id", "delay_minutes"],
        "output": "inflow delay what-if result",
        "use_when": "지하차도 유입이 N분 늦어졌다면/지연됐다면 이후 단계(주행불능·완전침수)가 언제가 되는지 물을 때. 차수벽·펌프 '때문에' 늦어졌다고 가정한 질문도 지연 분 값이 있으면 이 도구로 시간 이동만 계산한다.",
        "parameters": "delay_minutes: [정수 분, ...] 0~180, 최대 10개. 사용자가 쓴 분 값만 쓴다.",
        "can_say": "유입·주행불능·완전침수 시각이 각각 몇 시로 옮겨지는지(기록 시각 + 지연 분).",
        "cannot_say": "차수벽·펌프가 실제로 유입을 몇 분 늦추는지, 수위·침수 범위 변화. 지연 분은 사용자 가정이다.",
        "examples": ["유입이 10분 늦춰졌다면 주행불능 시각은?", "차수벽으로 유입이 30분 늦어졌다면?"],
    },
    {
        "name": "get_exposure_inventory",
        "description": "Count connected buildings, roads, and facilities inside focus-feature radius rings.",
        "input_fields": ["event_id", "radii_m"],
        "output": "exposure inventory, not flood impact estimate",
        "use_when": "지하차도 주변 반경 N m 안의 건물·도로·시설 수를 물을 때.",
        "parameters": "radii_m: [정수 m, ...] 사용자가 쓴 반경만 쓴다. 반경이 없으면 missing_parameter로 반경을 묻고 follow_ups에 500m·1000m 예시를 준다.",
        "can_say": "반경별 건물 수, 도로 길이(km), 연결된 시설 수와 자료 출처.",
        "cannot_say": "침수된 건물 수나 피해량. 반경 안에 있다는 것이지 침수됐다는 뜻이 아니다.",
        "examples": ["지하차도 반경 500m 안에 건물이 몇 개야?", "반경 1000m 주변 시설 알려줘"],
    },
    {
        "name": "compare_scenarios",
        "description": "Compare supported closure-timing or inflow-delay scenarios against a registered baseline.",
        "input_fields": ["event_id", "comparison_type", "closure_times", "delay_minutes"],
        "output": "baseline versus scenario timing comparison, not damage reduction",
        "use_when": "원시나리오(실제 기록)와 통제·지연 가정을 나란히 비교해 달라고 할 때.",
        "parameters": "comparison_type: closure_timing 또는 inflow_delay. 해당 값(closure_times 또는 delay_minutes)을 함께 준다.",
        "can_say": "기준 대비 각 단계 시각 차이.",
        "cannot_say": "피해 감소량.",
        "examples": ["원래 기록과 08:00 통제를 비교해줘"],
    },
    {
        "name": "analyze_hand_threshold",
        "description": "Compare HAND envelope grid cells after a user-defined reduction in its selection threshold. This is sensitivity only, not a verified barrier or levee effect.",
        "input_fields": ["event_id", "reduction_m"],
        "output": "selected and removed HAND cell IDs by incident stage",
        "use_when": "지도 침수 추정 셀(HAND)의 판정 기준·선택 임계를 낮추면 셀이 어떻게 바뀌는지 물을 때만.",
        "parameters": "reduction_m: 0~2.5 (m). 사용자가 HAND·셀·판정 기준과 함께 쓴 값만 쓴다. 제방·차수벽 높이(예: 제방 3m)를 이 값으로 바꾸지 않는다.",
        "can_say": "단계별 기준 셀 수, 변경 후 남은 셀 수, 제외된 셀 수.",
        "cannot_say": "제방·차수벽 효과, 실제 침수 범위·침수심 감소.",
        "examples": ["HAND 판정 기준을 1.5m 낮추면 선택 셀이 어떻게 바뀌나요?"],
    },
)


def list_agent_tools(event_id: str = "osong-2023") -> list[dict[str, Any]]:
    """Return a copy of the tools that are actually executable for this event."""

    if agent_cases.handles(event_id):
        return agent_cases.tools_for(event_id)
    return [dict(tool) for tool in _TOOL_CATALOG]


def _get_event(event_id: str, _: AgentToolCallRequest) -> dict[str, Any]:
    return get_event(event_id)


def _get_reconstruction(event_id: str, _: AgentToolCallRequest) -> dict[str, Any]:
    if agent_cases.handles(event_id):
        return agent_cases.reconstruction(event_id)
    if event_id != "osong-2023":
        raise ReconstructionUnavailable(
            f"Incident reconstruction timeline is not connected for {event_id}"
        )
    return get_osong_reconstruction()


_SUMMARY_KEYS = (
    "rainfall_peak_mm_per_hour", "rainfall_peak_timestamp", "rainfall_peak_station_name", "rainfall_records",
    "water_level_peak_m", "water_level_peak_timestamp", "water_level_peak_station_name",
    "response_window_min", "time_until_full_inundation_min",
    "building_count", "road_count", "waterway_count", "official_population", "official_population_unit",
)


def _get_observation_summary(event_id: str, _: AgentToolCallRequest) -> dict[str, Any]:
    if agent_cases.handles(event_id):
        return agent_cases.observation_summary(event_id)
    if event_id != "osong-2023":
        raise ReconstructionUnavailable(f"Observations are not connected for {event_id}")
    summary = get_osong_summary()
    return {
        **{key: summary.get(key) for key in _SUMMARY_KEYS if key in summary},
        "coverage_note": "Observed KMA AWS rainfall and flood-control-office water level; peaks are from the stored 2023-07-14~17 records.",
    }


def _analyze_closure_timing(event_id: str, request: AgentToolCallRequest) -> dict[str, Any]:
    closure_times = request.closure_times or ClosureTimingRequest().closure_times
    return ClosureTimingResult.model_validate(
        analyze_closure_timing(event_id, closure_times)
    ).model_dump()


def _analyze_inflow_delay(event_id: str, request: AgentToolCallRequest) -> dict[str, Any]:
    delay_minutes = request.delay_minutes or InflowDelayRequest().delay_minutes
    return InflowDelayResult.model_validate(
        analyze_inflow_delay(event_id, delay_minutes)
    ).model_dump()


def _analyze_hand_threshold(event_id: str, request: AgentToolCallRequest) -> dict[str, Any]:
    if request.reduction_m is None:
        raise ValueError("reduction_m is required for HAND threshold sensitivity")
    return analyze_hand_threshold(event_id, request.reduction_m)


def _get_exposure_inventory(event_id: str, request: AgentToolCallRequest) -> dict[str, Any]:
    radii_m = request.radii_m or [300, 500, 1000, 2000]
    return ExposureInventoryResult.model_validate(
        build_exposure_inventory(event_id, radii_m)
    ).model_dump()


def _compare_scenarios(event_id: str, request: AgentToolCallRequest) -> dict[str, Any]:
    reconstruction = _get_reconstruction(event_id, request)
    provenance = reconstruction.get("provenance", [])
    if request.comparison_type == "closure_timing":
        raw = analyze_closure_timing(
            event_id,
            request.closure_times or ClosureTimingRequest().closure_times,
        )
        result = {
            "event_id": event_id,
            "comparison_type": "closure_timing",
            "coverage_status": raw["coverage_status"],
            "coverage_note": raw["coverage_note"],
            "baseline": {
                "name": "Registered detection-trigger baseline",
                "closure_time": reconstruction["intervention"]["trigger_time"],
                "basis": reconstruction["intervention"]["trigger_basis"],
            },
            "comparisons": [
                {
                    "scenario": f"closure at {scenario['closure_time']}",
                    "closure_time": scenario["closure_time"],
                    "classification": scenario["classification"],
                    "minutes_before_underpass_inflow": scenario["minutes_before_underpass_inflow"],
                    "minutes_before_full_inundation": scenario["minutes_before_full_inundation"],
                    "lead_time_vs_detection_trigger_min": scenario["lead_time_vs_detection_trigger_min"],
                }
                for scenario in raw["scenarios"]
            ],
            "provenance": provenance,
            "assumptions": raw["assumptions"],
            "limitations": raw["limitations"] + [
                "This comparison reports timeline differences only; it does not estimate avoided damage or casualties."
            ],
        }
    else:
        requested = request.delay_minutes or InflowDelayRequest().delay_minutes
        raw = analyze_inflow_delay(event_id, [0, *requested])
        baseline = next(
            scenario for scenario in raw["scenarios"] if scenario["delay_minutes"] == 0
        )
        result = {
            "event_id": event_id,
            "comparison_type": "inflow_delay",
            "coverage_status": raw["coverage_status"],
            "coverage_note": raw["coverage_note"],
            "baseline": baseline,
            "comparisons": [
                scenario
                for scenario in raw["scenarios"]
                if scenario["delay_minutes"] != 0
            ],
            "provenance": provenance,
            "assumptions": raw["assumptions"],
            "limitations": raw["limitations"] + [
                "This comparison reports shifted milestone time only; it does not estimate hydraulic or damage reduction."
            ],
        }
    return ScenarioComparisonResult.model_validate(result).model_dump()


_HANDLERS: dict[str, ToolHandler] = {
    "get_event": _get_event,
    "get_reconstruction": _get_reconstruction,
    "get_observation_summary": _get_observation_summary,
    "analyze_closure_timing": _analyze_closure_timing,
    "analyze_inflow_delay": _analyze_inflow_delay,
    "analyze_hand_threshold": _analyze_hand_threshold,
    "get_exposure_inventory": _get_exposure_inventory,
    "compare_scenarios": _compare_scenarios,
}


def execute_agent_tool(
    tool_name: str,
    event_id: str,
    request: AgentToolCallRequest,
) -> dict[str, Any]:
    """Execute one registered tool and return only domain-derived values."""

    if tool_name in agent_cases.CASE_TOOL_PARAMETERS:
        if not agent_cases.handles(event_id):
            raise KeyError(f"{tool_name} is not registered for {event_id}")
        return agent_cases.run_tool(tool_name, event_id, request)
    handler = _HANDLERS.get(tool_name)
    if handler is None:
        raise KeyError(f"Unknown agent tool: {tool_name}")
    return handler(event_id, request)


def execute_agent_workflow(request: AgentWorkflowRequest) -> dict[str, Any]:
    """Run a small, deterministic multi-tool workflow.

    Natural-language intent planning can select this workflow later. For now,
    the workflow name is explicit so every tool call remains inspectable and
    reproducible.
    """

    tool_request = AgentToolCallRequest(
        event_id=request.event_id,
        closure_times=request.closure_times,
        delay_minutes=request.delay_minutes,
        radii_m=request.radii_m,
    )
    if request.workflow == "situation":
        analysis_tool = "get_reconstruction"
        tool_names = ["get_event", "get_reconstruction"]
    else:
        analysis_tool = {
            "closure_timing": "analyze_closure_timing",
            "inflow_delay": "analyze_inflow_delay",
            "exposure_inventory": "get_exposure_inventory",
        }[request.workflow]
        tool_names = ["get_event", analysis_tool]
        if request.workflow != "exposure_inventory":
            tool_names.insert(1, "get_reconstruction")
    tool_calls = []
    analysis_result: dict[str, Any] = {}
    context_result: dict[str, Any] = {}

    for order, tool_name in enumerate(tool_names, start=1):
        result = execute_agent_tool(tool_name, request.event_id, tool_request)
        if tool_name == analysis_tool:
            analysis_result = result
        if tool_name == "get_reconstruction":
            context_result = result
        tool_calls.append(
            {
                "order": order,
                "tool_name": tool_name,
                "status": "completed",
                "result_keys": sorted(result.keys()),
            }
        )

    provenance = analysis_result.get("provenance") or context_result.get("provenance")
    if not isinstance(provenance, list):
        provenance = analysis_result.get("inventory_sources", [])
    if not isinstance(provenance, list):
        provenance = []

    if request.workflow == "situation":
        coverage_status, coverage_note = "fallback", _SITUATION_COVERAGE_NOTE
    else:
        coverage_status = analysis_result.get("coverage_status")
        coverage_note = analysis_result.get("coverage_note")

    return {
        "workflow": request.workflow,
        "event_id": request.event_id,
        "status": "COMPLETED",
        "tool_calls": tool_calls,
        "result": analysis_result,
        "provenance": provenance,
        "coverage_status": coverage_status,
        "coverage_note": coverage_note,
    }


_CLOSURE_MARKERS = ("차단", "통제", "폐쇄", "closure", "close")
_INFLOW_MARKERS = ("유입", "차수벽", "inflow", "delay")
_EXPOSURE_MARKERS = ("건물", "도로", "시설", "노출", "반경", "exposure", "inventory")
_UNSUPPORTED_MARKERS = (
    "사망자",
    "사상자",
    "부상자",
    "피해액",
    "피해 비용",
    "피해율",
    "피해 감소",
    "침수심",
    "정확한 침수면적",
    "예측",
    "forecast",
    "casualt",
    "damage cost",
    "flood depth",
    "inundated area",
)
_SITUATION_COVERAGE_NOTE = (
    "Incident timestamps are reconstruction values whose confidence is NEEDS_SOURCE_PAGE. "
    "The spatial envelope is a derived approximation, not an official flood extent."
)
_SITUATION_MARKERS = (
    "상황",
    "재구성",
    "타임라인",
    "timeline",
    "replay",
    "reconstruction",
    "보여줘",
    "조회",
)

# Answerable questions, in the wording the deterministic planner actually routes.
# One source for the UI starter chips and for the suggestions attached to a refusal,
# so the two can never drift apart.
_EXAMPLE_QUESTIONS: tuple[dict[str, str], ...] = (
    {
        "workflow": "closure_timing",
        "label": "08:25 통제",
        "question": "08:25에 지하차도를 통제했다면 유입까지 몇 분 남나요?",
    },
    {
        "workflow": "inflow_delay",
        "label": "유입 30분 지연",
        "question": "차수벽으로 유입이 30분 늦어졌다면 어떻게 되나요?",
    },
    {
        "workflow": "exposure_inventory",
        "label": "반경 500m 재고",
        "question": "지하차도 반경 500m 안에 건물이 몇 개인가요?",
    },
    {
        "workflow": "situation",
        "label": "상황 타임라인",
        "question": "오송 침수 상황을 타임라인으로 보여주세요.",
    },
)


def list_example_questions(event_id: str = "osong-2023") -> list[dict[str, str]]:
    """Return the answerable starter questions the UI offers as chips."""

    if agent_cases.handles(event_id):
        return agent_cases.examples_for(event_id)
    return [dict(example) for example in _EXAMPLE_QUESTIONS]


def suggestions_for(workflows: tuple[str, ...] | None = None, event_id: str = "osong-2023") -> list[str]:
    """Questions this system can actually answer.

    A refusal that only says "no" is a dead end for the person asking. Every
    non-executable verdict carries these so the next step is one click away.
    ``workflows`` narrows the list to specific candidates; ``None`` offers all.
    """

    return [
        example["question"]
        for example in list_example_questions(event_id)
        if workflows is None or example["workflow"] in workflows
    ]


def _contains_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _extract_clock_times(text: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", text):
        hour, minute = int(match.group(1)), int(match.group(2))
        if hour > 23 or minute > 59:
            continue
        value = f"{hour:02d}:{minute:02d}"
        if value not in seen:
            values.append(value)
            seen.add(value)

    for match in re.finditer(r"(?<!\d)(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?", text):
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        if hour > 23 or minute > 59:
            continue
        value = f"{hour:02d}:{minute:02d}"
        if value not in seen:
            values.append(value)
            seen.add(value)
    return values


def _extract_minutes(text: str) -> list[int]:
    values: list[int] = []
    for match in re.finditer(r"(?<!\d)(\d{1,3})\s*(?:분|minutes?|mins?)", text):
        value = int(match.group(1))
        if 0 <= value <= 180 and value not in values:
            values.append(value)
    return values


def _extract_radii(text: str) -> list[int]:
    values: list[int] = []
    patterns = (
        r"(?:반경|radius)\s*(\d{2,5})\s*(?:m|미터)?",
        r"(?<!\d)(\d{2,5})\s*(?:m|미터)\s*(?:반경|권)?",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = int(match.group(1))
            if 50 <= value <= 20000 and value not in values:
                values.append(value)
    # "1km", "1.5 킬로", "2킬로미터" are radii in kilometres.
    for match in re.finditer(r"(?<![\d.])(\d{1,2}(?:\.\d)?)\s*(?:km|킬로미터|킬로)", text, re.IGNORECASE):
        value = int(round(float(match.group(1)) * 1000))
        if 50 <= value <= 20000 and value not in values:
            values.append(value)
    return values


def plan_agent_intent(request: AgentIntentPlanRequest) -> dict[str, Any]:
    """Map a small supported phrase set to an inspectable workflow plan.

    This is intentionally deterministic. It does not call an LLM, execute a
    tool, or turn an unrecognized request into a plausible-looking analysis.
    """

    text = " ".join(request.message.lower().split())
    has_closure = _contains_marker(text, _CLOSURE_MARKERS)
    # "유입까지" names the milestone to compare a closure against; it is not
    # a request to delay the water inflow itself.
    has_inflow = _contains_marker(text.replace("유입까지", ""), _INFLOW_MARKERS)
    has_exposure = _contains_marker(text, _EXPOSURE_MARKERS)
    has_situation = _contains_marker(text, _SITUATION_MARKERS)
    actionable = [
        workflow
        for workflow, matched in (
            ("closure_timing", has_closure),
            ("inflow_delay", has_inflow),
            ("exposure_inventory", has_exposure),
        )
        if matched
    ]

    base = {
        "status": "READY",
        "event_id": request.event_id,
        "parameters": {"event_id": request.event_id},
        "tool_names": [],
        "suggestions": [],
        "assumptions": [],
        "limitations": [
            "This plan selects registered deterministic tools; it does not execute them.",
            "The Agent must present the selected tool result and its provenance/limitations.",
        ],
    }

    if _contains_marker(text, _UNSUPPORTED_MARKERS):
        return {
            **base,
            "status": "UNSUPPORTED",
            "reason": "The request asks for an unregistered impact or forecast quantity.",
            "suggestions": suggestions_for(),
        }

    if len(actionable) > 1:
        return {
            **base,
            "status": "NEEDS_CLARIFICATION",
            "reason": "Multiple analysis intents were detected; choose one workflow.",
            "suggestions": suggestions_for(tuple(actionable)),
            "limitations": base["limitations"] + [
                f"Candidate workflows: {', '.join(actionable)}."
            ],
        }

    if actionable:
        workflow = actionable[0]
        parameters = base["parameters"]
        if workflow == "closure_timing":
            closure_times = _extract_clock_times(text)
            if closure_times:
                parameters["closure_times"] = closure_times
            else:
                base["assumptions"].append(
                    "No closure time was detected; the workflow default closure times will be used."
                )
            tool_names = ["get_event", "get_reconstruction", "analyze_closure_timing"]
            reason = "Detected an underpass closure/control timing request."
        elif workflow == "inflow_delay":
            delay_minutes = _extract_minutes(text)
            if delay_minutes:
                parameters["delay_minutes"] = delay_minutes
            else:
                base["assumptions"].append(
                    "No delay duration was detected; the workflow default delay values will be used."
                )
            tool_names = ["get_event", "get_reconstruction", "analyze_inflow_delay"]
            reason = "Detected an inflow-delay or barrier-assumption request."
        else:
            radii_m = _extract_radii(text)
            if radii_m:
                parameters["radii_m"] = radii_m
            else:
                base["assumptions"].append(
                    "No radius was detected; the workflow default radius rings will be used."
                )
            tool_names = ["get_event", "get_exposure_inventory"]
            reason = "Detected a radius-based exposure inventory request."
        return {
            **base,
            "workflow": workflow,
            "parameters": parameters,
            "tool_names": tool_names,
            "reason": reason,
        }

    if has_situation:
        return {
            **base,
            "workflow": "situation",
            "tool_names": ["get_event", "get_reconstruction"],
            "reason": "Detected a historical situation or replay request.",
            "assumptions": [
                "The replay shows stored reconstruction timestamps; no new value is computed.",
                "Spatial state comes from a derived HAND-like envelope, not an official flood extent.",
            ],
        }

    return {
        **base,
        "status": "UNSUPPORTED",
        "reason": "No registered FloodOps workflow matched the request.",
        "suggestions": suggestions_for(),
    }

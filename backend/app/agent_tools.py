"""Registered, deterministic tools for the future FloodOps Agent.

The tool layer delegates to existing domain services and repositories. It does
not read GIS files directly, call external APIs, or infer missing measurements.
"""

from collections.abc import Callable
import re
from typing import Any

from .data import get_event
from .osong_repository import get_osong_reconstruction
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


_TOOL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "get_event",
        "description": "Get the registered flood event and its current data status.",
        "input_fields": ["event_id"],
        "output": "registered event metadata",
    },
    {
        "name": "get_reconstruction",
        "description": "Get the connected historical reconstruction replay and provenance.",
        "input_fields": ["event_id"],
        "output": "historical reconstruction response",
    },
    {
        "name": "analyze_closure_timing",
        "description": "Compare hypothetical underpass closure times with observed reconstruction milestones.",
        "input_fields": ["event_id", "closure_times"],
        "output": "closure timing what-if result",
    },
    {
        "name": "analyze_inflow_delay",
        "description": "Shift downstream reconstruction milestones by an explicit inflow-delay assumption.",
        "input_fields": ["event_id", "delay_minutes"],
        "output": "inflow delay what-if result",
    },
    {
        "name": "get_exposure_inventory",
        "description": "Count connected buildings, roads, and facilities inside focus-feature radius rings.",
        "input_fields": ["event_id", "radii_m"],
        "output": "exposure inventory, not flood impact estimate",
    },
    {
        "name": "compare_scenarios",
        "description": "Compare supported closure-timing or inflow-delay scenarios against a registered baseline.",
        "input_fields": ["event_id", "comparison_type", "closure_times", "delay_minutes"],
        "output": "baseline versus scenario timing comparison, not damage reduction",
    },
)


def list_agent_tools() -> list[dict[str, Any]]:
    """Return a copy of the tools that are actually executable."""

    return [dict(tool) for tool in _TOOL_CATALOG]


def _get_event(event_id: str, _: AgentToolCallRequest) -> dict[str, Any]:
    return get_event(event_id)


def _get_reconstruction(event_id: str, _: AgentToolCallRequest) -> dict[str, Any]:
    if event_id != "osong-2023":
        raise ReconstructionUnavailable(
            f"Incident reconstruction timeline is not connected for {event_id}"
        )
    return get_osong_reconstruction()


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
    "analyze_closure_timing": _analyze_closure_timing,
    "analyze_inflow_delay": _analyze_inflow_delay,
    "get_exposure_inventory": _get_exposure_inventory,
    "compare_scenarios": _compare_scenarios,
}


def execute_agent_tool(
    tool_name: str,
    event_id: str,
    request: AgentToolCallRequest,
) -> dict[str, Any]:
    """Execute one registered tool and return only domain-derived values."""

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

    return {
        "workflow": request.workflow,
        "event_id": request.event_id,
        "status": "COMPLETED",
        "tool_calls": tool_calls,
        "result": analysis_result,
        "provenance": provenance,
        "coverage_status": analysis_result.get("coverage_status"),
        "coverage_note": analysis_result.get("coverage_note"),
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
        "question": "08:25에 지하차도를 통제했다면 어떻게 되나요?",
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


def list_example_questions() -> list[dict[str, str]]:
    """Return the answerable starter questions the UI offers as chips."""

    return [dict(example) for example in _EXAMPLE_QUESTIONS]


def suggestions_for(workflows: tuple[str, ...] | None = None) -> list[str]:
    """Questions this system can actually answer.

    A refusal that only says "no" is a dead end for the person asking. Every
    non-executable verdict carries these so the next step is one click away.
    ``workflows`` narrows the list to specific candidates; ``None`` offers all.
    """

    return [
        example["question"]
        for example in _EXAMPLE_QUESTIONS
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
    return values


def plan_agent_intent(request: AgentIntentPlanRequest) -> dict[str, Any]:
    """Map a small supported phrase set to an inspectable workflow plan.

    This is intentionally deterministic. It does not call an LLM, execute a
    tool, or turn an unrecognized request into a plausible-looking analysis.
    """

    text = " ".join(request.message.lower().split())
    has_closure = _contains_marker(text, _CLOSURE_MARKERS)
    has_inflow = _contains_marker(text, _INFLOW_MARKERS)
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
        }

    return {
        **base,
        "status": "UNSUPPORTED",
        "reason": "No registered FloodOps workflow matched the request.",
        "suggestions": suggestions_for(),
    }

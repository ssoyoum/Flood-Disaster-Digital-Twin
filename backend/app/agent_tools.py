"""Registered, deterministic tools for the future FloodOps Agent.

The tool layer delegates to existing domain services and repositories. It does
not read GIS files directly, call external APIs, or infer missing measurements.
"""

from collections.abc import Callable
from typing import Any

from .data import get_event
from .osong_repository import get_osong_reconstruction
from .schemas import (
    AgentToolCallRequest,
    ClosureTimingRequest,
    ClosureTimingResult,
    InflowDelayRequest,
    InflowDelayResult,
)
from .services import ReconstructionUnavailable, analyze_closure_timing, analyze_inflow_delay


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


_HANDLERS: dict[str, ToolHandler] = {
    "get_event": _get_event,
    "get_reconstruction": _get_reconstruction,
    "analyze_closure_timing": _analyze_closure_timing,
    "analyze_inflow_delay": _analyze_inflow_delay,
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

"""LLM-backed intent planner for the FloodOps Agent.

The model is given one job: pick a registered workflow and pull its parameters
out of the user's sentence. It never answers the flood question, and it never
produces an analysis number - every value the caller finally shows comes from
the deterministic Tool layer in ``services.py``.

Anything the model returns is re-validated against the registered workflow
names and the same parameter ranges the analysis endpoints enforce. If the API,
the credential, or the validation fails, the caller falls back to the
deterministic planner in ``agent_tools.py`` so behaviour never regresses.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from .agent_tools import _extract_clock_times, _extract_minutes, _extract_radii, suggestions_for
from .schemas import AgentIntentPlanRequest


MODEL_ID = "gemini-3.5-flash-lite"
MAX_TOKENS = 4000

# A demo runs on whatever network the venue provides. Without a bound, an
# unreachable API makes the request hang instead of falling back, so the rule
# planner never gets its turn. Fail fast and let the fallback answer.
DEFAULT_TIMEOUT_SECONDS = 10.0

_WORKFLOW_TOOLS: dict[str, list[str]] = {
    "closure_timing": ["get_event", "get_reconstruction", "analyze_closure_timing"],
    "inflow_delay": ["get_event", "get_reconstruction", "analyze_inflow_delay"],
    "exposure_inventory": ["get_event", "get_exposure_inventory"],
}

_SYSTEM_PROMPT = """You route a flood-analysis question to one registered workflow.

Registered workflows:
- closure_timing: the user asks what changes if the underpass entrance is closed at a
  different clock time. Parameter: closure_times, a list of "HH:MM" strings taken from
  the message.
- inflow_delay: the user assumes water inflow into the underpass starts later, for
  example because of a flood barrier. Parameter: delay_minutes, a list of whole minutes
  between 0 and 180 taken from the message.
- exposure_inventory: the user asks how many buildings, roads, or facilities sit within
  a distance of the focus feature. Parameter: radii_m, a list of radii in metres between
  50 and 20000 taken from the message.
- unsupported: anything else.

Rules:
- Choose unsupported when the question needs a quantity no registered workflow computes,
  such as casualties, injuries, damage cost, flood depth, or inundated area.
- Choose unsupported for anything outside flood analysis of the registered event.
- Only report a parameter value that is literally present in the message. Leave the list
  empty when the user gives no value; the workflow default is then used.
- Never answer the question, never estimate, and never invent a number.
- reason: one short English sentence naming the detected intent."""


class LlmPlannerUnavailable(RuntimeError):
    """The Gemini API cannot be used for this request."""


class LlmPlan(BaseModel):
    """Schema the model must fill. Routing only - no analysis values."""

    workflow: Literal["closure_timing", "inflow_delay", "exposure_inventory", "unsupported"]
    closure_times: list[str] = Field(default_factory=list, max_length=10)
    delay_minutes: list[int] = Field(default_factory=list, max_length=10)
    radii_m: list[int] = Field(default_factory=list, max_length=10)
    reason: str = Field(min_length=1, max_length=300)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_env_file_loaded = False


def _load_env_file_once() -> None:
    """Make a local ``.env`` credential visible to the app.

    uvicorn only reads ``.env`` when started with ``--env-file`` and pytest never
    does, so a key pasted into ``.env`` would otherwise be invisible here. Real
    environment variables always win over the file.
    """

    global _env_file_loaded
    if _env_file_loaded:
        return
    _env_file_loaded = True
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv(_REPO_ROOT / ".env", override=False)


def _timeout_seconds() -> float:
    """Read the request timeout after ``.env`` has had its chance to load."""

    raw = os.environ.get("AGENT_LLM_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def llm_planner_model_id() -> str:
    """Use the configured Gemini model while keeping the default explicit."""

    _load_env_file_once()
    return (os.environ.get("GEMINI_MODEL") or MODEL_ID).strip()


def llm_planner_status() -> dict[str, Any]:
    """Report whether the LLM planner can run, without calling the API."""

    _load_env_file_once()
    model = llm_planner_model_id()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
        return {
            "available": False,
            "reason": "GEMINI_MODEL is not a valid model ID.",
            "timeout_seconds": _timeout_seconds(),
        }
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        return {
            "available": False,
            "reason": "No Gemini API credential is configured.",
            "timeout_seconds": _timeout_seconds(),
        }
    return {
        "available": True,
        "reason": f"Ready on {model}.",
        "timeout_seconds": _timeout_seconds(),
    }


def _gemini_plan(message: str) -> LlmPlan:
    """Ask Gemini for JSON routing data; never send an analysis tool result."""

    status = llm_planner_status()
    if not status["available"]:
        raise LlmPlannerUnavailable(status["reason"])
    model = llm_planner_model_id()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(model, safe='')}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0,
            "maxOutputTokens": MAX_TOKENS,
        },
    }
    try:
        response = httpx.post(
            url,
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"].strip()},
            json=payload,
            timeout=_timeout_seconds(),
        )
    except httpx.HTTPError as exc:
        raise LlmPlannerUnavailable(f"Gemini connection failed: {type(exc).__name__}.") from exc
    if response.status_code != 200:
        raise LlmPlannerUnavailable(f"Gemini API returned HTTP {response.status_code}.")
    try:
        candidates = response.json()["candidates"]
        parts = candidates[0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
        return LlmPlan.model_validate_json(text)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError("Gemini returned no valid routing plan.") from exc


def _validated_parameters(
    plan: LlmPlan, event_id: str, message: str | None = None
) -> dict[str, Any]:
    """Keep only literal question values and re-check the tool ranges."""

    parameters: dict[str, Any] = {"event_id": event_id}
    if plan.workflow == "closure_timing":
        model_times: list[str] = []
        for value in plan.closure_times:
            hour, _, minute = value.partition(":")
            if not (hour.isdigit() and minute.isdigit() and int(hour) < 24 and int(minute) < 60):
                raise ValueError(f"LLM returned an invalid closure time: {value!r}")
            model_times.append(f"{int(hour):02d}:{int(minute):02d}")
        literal = _extract_clock_times(message.lower()) if message is not None else None
        if literal is not None and any(value not in literal for value in model_times):
            raise ValueError("LLM returned a closure time absent from the question.")
        values = literal if literal is not None else model_times
        if values:
            parameters["closure_times"] = values
    elif plan.workflow == "inflow_delay":
        if any(not 0 <= minutes <= 180 for minutes in plan.delay_minutes):
            raise ValueError(f"LLM returned an out-of-range delay: {plan.delay_minutes}")
        literal = _extract_minutes(message.lower()) if message is not None else None
        if literal is not None and any(value not in literal for value in plan.delay_minutes):
            raise ValueError("LLM returned a delay absent from the question.")
        values = literal if literal is not None else plan.delay_minutes
        if values:
            parameters["delay_minutes"] = values
    elif plan.workflow == "exposure_inventory":
        if any(not 50 <= radius <= 20000 for radius in plan.radii_m):
            raise ValueError(f"LLM returned an out-of-range radius: {plan.radii_m}")
        literal = _extract_radii(message.lower()) if message is not None else None
        if literal is not None and any(value not in literal for value in plan.radii_m):
            raise ValueError("LLM returned a radius absent from the question.")
        values = literal if literal is not None else plan.radii_m
        if values:
            parameters["radii_m"] = values
    return parameters


def plan_with_llm(request: AgentIntentPlanRequest) -> dict[str, Any]:
    """Return the same plan shape as the deterministic planner.

    Raises ``LlmPlannerUnavailable`` when the planner cannot run and
    ``ValueError`` when the model returns something the registry rejects. The
    caller treats both as a reason to fall back, never as an analysis result.
    """

    plan = _gemini_plan(request.message)

    limitations = [
        "This plan selects registered deterministic tools; it does not execute them.",
        "The Agent must present the selected tool result and its provenance/limitations.",
        "The model only routed the request and extracted parameters. Every reported value "
        "comes from the deterministic tool layer.",
    ]
    if plan.workflow == "unsupported":
        return {
            "status": "UNSUPPORTED",
            "event_id": request.event_id,
            "workflow": None,
            "parameters": {"event_id": request.event_id},
            "tool_names": [],
            "reason": plan.reason,
            "suggestions": suggestions_for(),
            "assumptions": [],
            "limitations": limitations,
        }

    parameters = _validated_parameters(plan, request.event_id, request.message)
    assumptions = []
    if len(parameters) == 1:
        assumptions.append(
            "No parameter value was present in the message; the workflow default will be used."
        )
    return {
        "status": "READY",
        "event_id": request.event_id,
        "workflow": plan.workflow,
        "parameters": parameters,
        "tool_names": _WORKFLOW_TOOLS[plan.workflow],
        "reason": plan.reason,
        "suggestions": [],
        "assumptions": assumptions,
        "limitations": limitations,
    }

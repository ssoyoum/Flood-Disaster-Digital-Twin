"""Resolve explicit follow-ups from user turns without borrowing assistant numbers."""

from dataclasses import dataclass
import re
from typing import Any, Callable

from . import agent_cases
from .schemas import AgentAskRequest

Router = Callable[[str, str], list[dict[str, Any]]]
_FOLLOW_UP = re.compile(r"(?:그|같은|앞선|이전|아까|방금|해당)\s*(?:조건|시각|기준|가정|결과|분석|질문)|그럼|다시\s*비교|이어서")
_OTHER_EFFECT = re.compile(r"제방|차수벽|펌프|배수시설|사망|인명|피해|침수심|유속|예측|침수\s*면적")
_TOPICS = {
    "analyze_closure_timing": r"통제|차단|폐쇄",
    "analyze_inflow_delay": r"유입|지연",
    "analyze_hand_threshold": r"HAND|셀|임계",
    "get_exposure_inventory": r"반경|주변|재고",
    "analyze_alert_timing": r"경보|문자|알림",
    "analyze_storage_capture": r"터널|저류",
}
_LABELS = {
    "analyze_closure_timing": "지하차도 통제",
    "analyze_inflow_delay": "유입 지연",
    "analyze_hand_threshold": "HAND 선택 임계",
    "get_exposure_inventory": "반경",
    "analyze_alert_timing": "저지대 경보",
    "analyze_storage_capture": "저류시설",
}


@dataclass
class QuestionContext:
    hints: list[dict[str, Any]]
    parameter_text: str
    mode: str = "current"
    note: str = ""


def _analysis_hints(hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [hint for hint in hints if hint["tool_name"] in {*_LABELS, "analyze_response_timing"}]


def resolve_question(request: AgentAskRequest, router: Router) -> QuestionContext:
    direct = router(request.message, request.event_id)
    current = QuestionContext(direct, request.message)
    if direct or not _FOLLOW_UP.search(request.message) or _OTHER_EFFECT.search(request.message):
        return current
    ambiguous = QuestionContext([], request.message, "ambiguous",
                                "이어 사용할 분석 조건을 하나로 확인하지 못했습니다. 분석 종류와 시각·수치 조건을 함께 적어 주세요.")
    user_index = next((index for index in range(len(request.history) - 1, -1, -1)
                       if request.history[index].role == "user"), None)
    if user_index is None:
        return ambiguous
    # A chain of follow-ups is bounded by the request's six-message history.
    prior = resolve_question(AgentAskRequest(event_id=request.event_id,
                                            message=request.history[user_index].content[:1000],
                                            history=request.history[:user_index]), router)
    analyses = _analysis_hints(prior.hints)
    if len(analyses) != 1:
        return ambiguous
    hint = analyses[0]
    name = hint["tool_name"]
    mentioned = {tool for tool, pattern in _TOPICS.items() if re.search(pattern, request.message, re.IGNORECASE)}
    if mentioned and name not in mentioned:
        return ambiguous
    if name == "analyze_response_timing":
        intervention = agent_cases.intervention_for(request.event_id, request.message)
        if intervention and intervention["id"] != hint["parameters"]["intervention_id"]:
            return ambiguous
    if not re.search(r"\d", request.message):
        return QuestionContext([hint], f"{prior.parameter_text}\n{request.message}", "reused",
                               "직전 사용자 질문의 분석 조건을 이어 사용했습니다.")
    if re.search(r"[-−]\s*\d|\d+\.\d+\s*(?:분|minutes?|mins?)", request.message):
        return ambiguous
    if name == "analyze_inflow_delay" and re.search(r"\d{1,2}:\d{2}|\d+\s*시", request.message):
        return ambiguous
    # Relative shifts can mean the previous assumption or the recorded baseline.
    if re.search(r"일찍|늦게|앞당|늦춰|더", request.message):
        return ambiguous
    label = _LABELS.get(name)
    if name == "analyze_response_timing":
        label = next(item["name"] for item in agent_cases.TIMELINE_CASES[request.event_id]["interventions"]
                     if item["id"] == hint["parameters"]["intervention_id"])
    text = f"{label} {request.message}"
    updates = _analysis_hints(router(text, request.event_id))
    if len(updates) != 1 or updates[0]["tool_name"] != name or not updates[0]["parameters"]:
        return ambiguous
    # Do not silently drop an earlier independent condition (e.g. capacity).
    if set(hint["parameters"]) - set(updates[0]["parameters"]):
        return ambiguous
    return QuestionContext(updates, text, "updated", "앞선 분석 종류에 이번 질문의 새 조건을 적용했습니다.")

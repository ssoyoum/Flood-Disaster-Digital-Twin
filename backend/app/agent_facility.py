"""Read-only facility Agent tools. Observations, rules and backtests remain distinct."""

from datetime import datetime, timedelta, timezone
import re
from typing import Any

from .services import ReconstructionUnavailable

TOOL_NAMES = {"get_facility_status", "get_control_rule", "get_facility_backtest"}
EXAMPLES = [
    {"workflow": "facility_status", "label": "시설 상태", "question": "선택한 시설의 관측 상태와 수위 여유를 설명해줘"},
    {"workflow": "control_rule", "label": "통제 기준", "question": "통제 검토 기준과 그 근거는 무엇인가요?"},
    {"workflow": "facility_backtest", "label": "과거 백테스트", "question": "과거 수위 백테스트에서 언제 통제 검토가 시작됐나요?"},
]


def require_facility(facility_id: str, event_id: str) -> dict[str, Any]:
    from .twin import FACILITIES
    facility = FACILITIES[facility_id]
    if facility["event_id"] != event_id:
        raise ValueError("The selected facility does not belong to this event.")
    return facility


def tools(facility_id: str, event_id: str) -> list[dict[str, Any]]:
    require_facility(facility_id, event_id)
    descriptions = [
        ("get_facility_status", "선택 시설의 관측 모드·수위·관측 시각·단계·상승 속도·계획홍수위 여유를 설명한다.",
         "관측 모드와 시각, 자료 신선도, 통제 검토 권고. replay는 과거 재생이라고 명시한다.",
         "침수심, 확정 유입 시각, 예보, 실제 통제 명령, 오래된 관측으로 현재 안전 보장."),
        ("get_control_rule", "선택 시설에 등록된 통제 검토 규칙과 근거·한계를 설명한다.",
         "등록 수위·상승 속도 조건, 규칙 가정, 현장 계측·관리기관 판단 필요.",
         "미확인 법정 기준을 확정하거나 통제를 승인·실행."),
        ("get_facility_backtest", "저장된 사건 수위에 같은 규칙을 적용한 과거 백테스트를 설명한다.",
         "처음 통제 검토 시각, 기록된 유입·붕괴까지 시간, DQ-009 시각 차이.",
         "대피 성공·피해 감소·현재 위험 예측, 백테스트 권고를 실제 통제 기록으로 표현."),
    ]
    return [{"name": name, "description": description, "input_fields": ["facility_id", "observation_at"],
             "output": "facility-scoped evidence with provenance and limitations", "use_when": description,
             "parameters": "파라미터는 {}. 시설·관측 재생 시각은 화면에서 선택한 값으로 서버가 고정한다.",
             "can_say": can_say, "cannot_say": cannot_say, "examples": [EXAMPLES[index]["question"]]}
            for index, (name, description, can_say, cannot_say) in enumerate(descriptions)]


def hints(message: str) -> list[dict[str, Any]]:
    names = []
    historical = bool(re.search(r"백테스트|과거|2023|언제.*검토|재구성", message))
    present = bool(re.search(r"지금|현재", message))
    if re.search(r"지금|현재|상태|관측|여유|상승|수위|안전", message) and (not historical or present):
        names.append("get_facility_status")
    if re.search(r"기준|규칙|근거|왜|판단", message):
        names.append("get_control_rule")
        if "왜" in message and (not historical or present):
            names.append("get_facility_status")
    if historical:
        names.append("get_facility_backtest")
    return [{"tool_name": name, "parameters": {}} for name in dict.fromkeys(names)]


def _facility_info(facility: dict[str, Any]) -> dict[str, Any]:
    return {key: facility[key] for key in ("id", "name", "kind", "driver", "location", "road", "managing_agency", "event_id")}


def run_tool(name: str, event_id: str, request: Any) -> dict[str, Any]:
    from . import twin
    if name not in TOOL_NAMES or not request.facility_id:
        raise KeyError("Unknown facility Agent tool or missing facility scope.")
    facility = require_facility(request.facility_id, event_id)
    if name == "get_control_rule":
        rule = {key: value for key, value in facility["control_rule"].items() if key != "official_closure_trigger"}
        return {"facility_id": facility["id"], "facility": _facility_info(facility), "rule": rule,
                "levels_m": facility["gauge"]["levels_m"], "source": facility["gauge"]["source"],
                "coverage_note": "REGISTERED_RULE: this is a review rule, not an official closure order.",
                "limitations": ["상승 속도 조건은 트윈의 가정이다. 실제 통제는 현장 침수심 계측·관리기관 기준·담당자 판단이 우선한다.",
                                "침수심 통제 기준의 최신 공식 원문은 이 도구에 연결되지 않았다."]}
    if name == "get_facility_backtest":
        return {**twin.backtest(facility["id"]), "mode": "historical_backtest",
                "coverage_note": "NEEDS_SOURCE_PAGE: reference incident times require source-page verification.",
                "limitations": ["같은 규칙의 과거 수위 백테스트이며 실제 통제·인명·피해 감소를 계산하지 않았다."]}
    try:
        if request.observation_at:
            now = datetime.fromisoformat(request.observation_at.replace("Z", "+00:00"))
            if now.tzinfo is not None:
                now = now.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
            source = twin.ReplaySource()
            result = twin.assess(facility, source.window(facility["gauge"]["station_id"], now, 120), now,
                                 source.rain_window(facility["rain_station"]["station_id"], now, 360))
            result.update({"mode": "replay", "facility": _facility_info(facility)})
        else:
            if twin.twin_mode()["mode"] == "live":
                now_kst = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None, second=0, microsecond=0)
                result = twin.facility_status(facility["id"], now_kst.isoformat())
            else:
                result = twin.facility_status(facility["id"])
    except Exception as exc:
        # Live source errors may contain a key-bearing URL. Never return that text.
        raise ReconstructionUnavailable("Facility observation source unavailable; no historical data was substituted.") from exc
    observation = result.get("observation") or {}
    max_age = 90 if observation.get("interval") == "1H" else 20
    quality = "missing" if not observation else "stale" if observation.get("age_min", 0) > max_age else "fresh"
    return {**result, "observation_quality": quality, "freshness_policy_max_age_min": max_age,
            "decision_usable": result["mode"] == "live" and quality == "fresh" and result.get("recommendation") is not None,
            "coverage_note": "HISTORICAL_REPLAY: past observations, not the present state." if result["mode"] == "replay" else "LIVE_OBSERVATION: check observation age before interpretation.",
            "limitations": [*result.get("limitations", []), "관측 신선도 기준은 이 Agent의 내부 검토 규칙이며 법정 통제 기준이 아니다."]}


def summarize(calls: list[dict[str, Any]]) -> tuple[str, list[int]]:
    """Render only tool-derived fields; do not need a model to explain basic evidence."""
    sentences, evidence = [], []
    for call in calls:
        name, result, order = call["tool_name"], call["result"], call["order"]
        text = ""
        if name == "get_facility_status":
            observation = result.get("observation")
            if not observation:
                text = "선택 시각에 연결된 관측이 없어 수위 상태를 판단할 수 없습니다."
            else:
                mode = "과거 재생" if result["mode"] == "replay" else "실시간 관측"
                text = f"{mode}의 관측 시각 {observation['time']} 기준 수위는 {observation['water_level_m']}m, 단계는 {result['stage_label']}입니다."
                if result["observation_quality"] == "stale":
                    text += f" 관측이 {observation['age_min']}분 전 자료여서 현재 통제 판단에 사용할 수 없습니다."
                else:
                    text += f" 계획홍수위까지 여유는 {result['margin_to_planned_flood_m']}m입니다."
                    if result["recommendation"] == "CLOSURE_REVIEW":
                        text += " 등록 규칙에 따라 통제 검토가 필요합니다. 실제 통제 결정·실행을 뜻하지 않습니다."
                text += " 과거 재생을 현재 상태로 해석하지 않으며 상승 속도 외삽은 예보나 유입 예측이 아닙니다."
        elif name == "get_control_rule":
            levels, rule = result["levels_m"], result["rule"]
            text = (f"등록 규칙은 계획홍수위 {levels['planned_flood']}m에 도달했거나, 경보 수위 {levels['warning']}m 이상에서 "
                    f"상승 속도 외삽의 계획홍수위 도달 시간이 {rule['lead_threshold_min']}분 이하이면 통제 검토를 제안합니다. "
                    "상승 속도 조건은 가정이며 현장 계측·관리기관 판단이 우선합니다.")
        elif name == "get_facility_backtest":
            first = result.get("first_closure_review")
            text = "저장된 과거 수위 백테스트에서 통제 검토 조건에 도달한 기록이 없습니다."
            if first:
                text = f"과거 수위 백테스트의 첫 통제 검토 시각은 {first['time']}입니다."
                if result.get("lead_minutes"):
                    text += f" 재구성된 유입 시각까지 {result['lead_minutes']['underpass_inflow']}분 앞섭니다."
                text += " 백테스트 권고이며 실제 통제·피해 감소 결과가 아닙니다."
            text += f" {result['note']}"
        if text:
            sentences.append(f"{text} [{order}]")
            evidence.append(order)
    return "\n".join(sentences), evidence


def safe_model_answer(answer: str, calls: list[dict[str, Any]]) -> bool:
    if re.search(r"현재\s*안전|지금\s*안전|안전합니다|위험이?\s*없|통제(?:를)?\s*(?:실행|승인|완료)|통제.*불필요|자동\s*차단|침수가?\s*없|피해가?\s*줄|대피\s*성공", answer):
        return False
    for call in calls:
        if call["tool_name"] == "get_facility_status":
            result = call["result"]
            if result["observation_quality"] != "fresh":
                return False
            if result["mode"] == "replay" and not re.search(r"과거|재생", answer):
                return False
    return True

"""Cross-case summary: the actual response time against one registered counterfactual time, per case.

Every number comes from the per-case analysis functions the consoles already use, so this page cannot
drift from them. Lead time = minutes between the response and the case's reference milestone.
"""

from typing import Any

from .seoul_repository import analyze_alert_timing
from .services import analyze_closure_timing
from .timeline_cases import analyze_response_timing


def _osong() -> dict[str, Any]:
    rows = {row["closure_time"][11:16]: row for row in analyze_closure_timing("osong-2023", ["06:40"])["scenarios"]}
    counterfactual = rows["06:40"]
    return {
        "event_id": "osong-2023",
        "case": "2023 오송 지하차도",
        "response": "지하차도 진입 통제",
        "milestone": "지하차도 유입 08:27",
        "actual": {"time": None, "lead_min": None, "label": "통제하지 않음"},
        "counterfactual": {
            "time": "06:40",
            "lead_min": counterfactual["minutes_before_underpass_inflow"],
            "label": "계획홍수위 도달(국무조정실이 통제 요건 충족으로 본 시각)에 통제",
        },
        "evidence": "재구성 시각, 출처 쪽수 확인 필요",
    }


def _seoul() -> dict[str, Any]:
    result = analyze_alert_timing(thresholds_mm_per_hour=[95])
    counterfactual = result["scenarios"][0]
    return {
        "event_id": "seoul-2022",
        "case": "2022 서울 도림천",
        "response": "저지대 침수 경보",
        "milestone": "신림동 첫 구조 신고 20:59",
        "actual": {"time": "21:19", "lead_min": -result["actual_alert_after_rescue_call_min"], "label": "서울시 첫 저지대 문자"},
        "counterfactual": {
            "time": counterfactual["alert_time"][11:16],
            "lead_min": counterfactual["minutes_before_first_rescue_call"],
            "label": "신림P 60분 강우가 설계강우 95 mm를 넘은 순간 경보",
        },
        "evidence": "강우 임계는 관측, 신고·문자 시각은 언론 보도",
    }


def _timeline(event_id: str, case: str, response: str, intervention_id: str, action: str, milestone_state: str, milestone_label: str, label: str) -> dict[str, Any]:
    result = analyze_response_timing(event_id, intervention_id, [action])
    by_time = {row["action_time"][11:16]: row for row in result["scenarios"]}
    actual_time = result["actual_time"][11:16]
    return {
        "event_id": event_id,
        "case": case,
        "response": response,
        "milestone": milestone_label,
        "actual": {"time": actual_time, "lead_min": by_time[actual_time]["minutes_before_milestones"][milestone_state], "label": result["actual_label"]},
        "counterfactual": {"time": action, "lead_min": by_time[action]["minutes_before_milestones"][milestone_state], "label": label},
        "evidence": "언론 보도 시각",
    }


def get_case_lead_times() -> dict[str, Any]:
    return {
        "measure": "minutes between the response and the case's reference milestone; negative means after it",
        "cases": [
            _osong(),
            _seoul(),
            _timeline("pohang-2022", "2022 포항 냉천", "지하주차장 진입 금지 안내", "parking_entry_ban", "06:00",
                      "parking_inflow", "지하주차장 침수 시작 06:37", "냉천 범람 시작 시각에 진입 금지 안내"),
            _timeline("andong-uiseong-2026", "2026 안동·의성", "대피명령", "evacuation_order", "23:40",
                      "predicted_warning_level", "미천 경보 수위 도달 예측 00:30", "미천 홍수경보와 동시에 대피명령"),
        ],
        "limitations": [
            "선행 시간은 기록된 시각 사이의 산술이며 대피 성공·인명·피해 감소를 뜻하지 않는다.",
            "사례마다 기준 사건과 근거 수준이 다르다. 사례 간 수치를 순위로 비교하지 않는다.",
        ],
    }

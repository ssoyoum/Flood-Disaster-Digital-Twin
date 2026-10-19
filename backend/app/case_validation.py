"""Validation cases: when would the facility risk rule have spoken, against the official forecast and the real control.

The national board ranks every facility live. Its thresholds (river stage, KMA heavy-rain amounts, official
forecasts as a floor) are only worth something if they speak before the people who closed the facility did, or
before the water got in when nobody closed it. Each case here replays `facility_risk()` every STEP_MINUTES over
one event and records, per facility and for the whole region:

- the first time the rule reached 주의(2) and 경계(3), and why,
- the first official 홍수주의보·홍수경보 at the facility's gauge (collected history),
- the reported control (or, for 오송, the inflow nobody stopped) and the lead of each signal over it.

Control times come from news reports (docs/PLATFORM_DATA.md) and are often only an upper bound ("06:01 보도 시점에
이미 통제") or approximate ("6시께"); `precision` says which, and the verdict never claims more than that allows.

The sweep takes a few minutes, so `data/scripts/build_case_validation.py` stores it in SCORECARD_FILE and the API
serves the stored file.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import facility_risk as fr
from . import flood_forecast as ff
from . import national_watch as nw

REPO_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_FILE = REPO_ROOT / "data" / "processed" / "validation" / "case_scorecard.json"
STEP_MINUTES = 10

CASES: list[dict[str, Any]] = [
    {
        "id": "osong-2023", "title": "오송 궁평2지하차도 2023-07-15", "region": "충북",
        "start": "2023-07-14T12:00", "end": "2023-07-15T08:40",
        "facility_ids": ["gungpyeong2-underpass"], "gauge": "3011665",
        "reference": {"at": "2023-07-15T08:27", "precision": "minute", "kind": "inflow",
                      "label": "통제 없이 지하차도 유입 시작(08:40 완전 침수)",
                      "source": "국무조정실 감찰 결과 시각(osong_repository, 원문 쪽수 미연결)"},
    },
    {
        "id": "daejeon-2020-07-30", "title": "대전 만년지하차도 2020-07-30", "region": "대전",
        "start": "2020-07-30T00:00", "end": "2020-07-30T09:00",
        "facility_ids": ["underpass_coordinates:321"], "gauge": "3009670",
        "reference": {"at": "2020-07-30T06:01", "precision": "upper_bound", "kind": "control",
                      "label": "만년·태평 지하차도 통제(새벽부터, 06:01 보도 시점에 통제 중)",
                      "source": "https://www.ytn.co.kr/_ln/0115_202007300601136499"},
    },
    {
        "id": "daejeon-2023-07-14", "title": "대전 하상도로·하상주차장 2023-07-14", "region": "대전",
        "start": "2023-07-14T00:00", "end": "2023-07-14T15:00",
        "facility_ids": ["underpass_coordinates:321", "underpass_coordinates:335"], "gauge": "3009670",
        "reference": {"at": "2023-07-14T05:30", "precision": "approximate", "kind": "control",
                      "label": "하상도로·하상주차장 16곳 출입 제한(05:30경)",
                      "source": "https://www.ccnnews.co.kr/news/articleView.html?idxno=301544"},
    },
    {
        "id": "daejeon-2024-07-10", "title": "대전 갑천 교량·오량지하차도 2024-07-10", "region": "대전",
        "start": "2024-07-10T00:00", "end": "2024-07-10T09:00",
        "facility_ids": ["underpass_coordinates:324", "underpass_coordinates:321"], "gauge": "3009670",
        "reference": {"at": "2024-07-10T06:00", "precision": "approximate", "kind": "control",
                      "label": "교량 8곳·오량지하차도 양방향 통제(6시께부터)",
                      "source": "https://m.joongdo.co.kr/view.php?key=20240710010003018"},
    },
]
PRECISION_KO = {"minute": "분 단위 기록", "approximate": "보도의 «경» 시각", "upper_bound": "보도 시각(그 전에 이미 통제)"}


def case(case_id: str) -> dict[str, Any]:
    for item in CASES:
        if item["id"] == case_id:
            return item
    raise ValueError(f"unknown validation case: {case_id}")


def _steps(start: str, end: str) -> list[str]:
    moment, stop, out = datetime.fromisoformat(start), datetime.fromisoformat(end), []
    while moment <= stop:
        out.append(moment.isoformat(timespec="seconds"))
        moment += timedelta(minutes=STEP_MINUTES)
    return out


def _lead(signal_at: str | None, reference_at: str) -> int | None:
    if not signal_at:
        return None
    return int((datetime.fromisoformat(reference_at) - datetime.fromisoformat(signal_at)).total_seconds() // 60)


def _verdict(lead: int | None, precision: str, kind: str) -> str:
    target = "유입" if kind == "inflow" else "실제 통제"
    if lead is None:
        return f"구간 안에서 울리지 않음({target}까지)"
    if precision == "upper_bound":
        return f"{target} 보도 시각보다 {lead}분 먼저" if lead >= 0 else f"{target} 보도 시각보다 {-lead}분 늦음, 그 전에 이미 통제 중"
    if precision == "approximate":
        return f"{target}보다 약 {lead}분 먼저" if lead >= 0 else f"{target}보다 약 {-lead}분 늦음"
    return f"{target}보다 {lead}분 먼저" if lead >= 0 else f"{target}보다 {-lead}분 늦음"


def _official_firsts(gauge: str, start: str, end: str) -> dict[str, dict[str, Any] | None]:
    """First time the gauge was under 주의보-or-higher and under 경보, counting an issuance still active at `start`."""
    lo, hi = datetime.fromisoformat(start), datetime.fromisoformat(end)
    out: dict[str, dict[str, Any] | None] = {"advisory": None, "warning": None}

    def mark(row: dict[str, Any], level: str) -> None:
        for key in ("advisory", "warning"):
            if out[key] is None and fr.OFFICIAL_LEVEL[level] >= fr.OFFICIAL_LEVEL[key]:
                out[key] = {"issued_at": row["issued_at"], "kind": row["kind"], "station_name": row["station_name"]}

    active = ff.active_at(lo).get(gauge)
    if active:
        mark({**active, "station_name": active["station_name"]}, active["level"])
    for row in ff.history():
        if row["station_code"] != gauge or not row["issued_at"] or not lo < datetime.fromisoformat(row["issued_at"]) <= hi:
            continue
        level = ff.level_of(row["kind"])
        if level:
            mark(row, level)
    return out


def compute(case_id: str, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    """Replay one case every STEP_MINUTES (slow: one facility_risk call per step); start/end narrow it for checks."""
    spec = {**case(case_id), **({"start": start} if start else {}), **({"end": end} if end else {})}
    region = nw.match_region(spec["region"])
    ref = spec["reference"]
    firsts: dict[str, dict[str, Any]] = {fid: {} for fid in spec["facility_ids"]}
    names: dict[str, str] = {}
    region_first: dict[str, dict[str, Any]] = {}
    region_at_reference: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = []
    for at in _steps(spec["start"], spec["end"]):
        data = fr.facility_risk(at, region=region, limit=2000)
        rows = data["facilities"]
        by_id = {r["facility_id"]: r for r in rows}
        for fid in spec["facility_ids"]:
            row = by_id.get(fid)
            if not row:
                continue
            names[fid] = row["name"]
            for level in (2, 3):
                if row["level"] >= level and str(level) not in firsts[fid]:
                    firsts[fid][str(level)] = {"at": at[:16], "why": row["why"], "driver": row["driver"]}
        for level in (2, 3):
            hit = [r for r in rows if r["level"] >= level]
            if hit and str(level) not in region_first:
                top = hit[0]
                region_first[str(level)] = {"at": at[:16], "count": len(hit), "first_facility": top["name"], "why": top["why"]}
        watched = [by_id.get(fid) for fid in spec["facility_ids"]]
        timeline.append({"at": at[:16], "levels": {fid: (r["level"] if r else None) for fid, r in zip(spec["facility_ids"], watched)},
                         "region_advisory_or_above": sum(1 for r in rows if r["level"] >= 2)})
        if region_at_reference is None and at[:16] >= ref["at"]:
            region_at_reference = {"at": at[:16], "advisory_or_above": sum(1 for r in rows if r["level"] >= 2),
                                   "warning_or_above": sum(1 for r in rows if r["level"] >= 3), "total": len(rows)}
    official = _official_firsts(spec["gauge"], spec["start"], spec["end"])

    def signal(label: str, at: str | None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        lead = _lead(at, ref["at"])
        verdict = _verdict(lead, ref["precision"], ref["kind"])
        at_start = at is not None and at[:16] <= spec["start"][:16]
        if at_start:  # already up when the replay began: the real first time is earlier, so the lead is a lower bound
            verdict = f"재생 시작({spec['start'][11:16]}) 전부터 · {verdict} 이상"
        return {"signal": label, "at": at, "lead_min": lead, "lead_is_lower_bound": at_start, "verdict": verdict, **(extra or {})}

    signals = [signal("공식 홍수주의보", (official["advisory"] or {}).get("issued_at"), {"source": "HRFCO fldfct 이력"}),
               signal("공식 홍수경보", (official["warning"] or {}).get("issued_at"), {"source": "HRFCO fldfct 이력"})]
    for fid in spec["facility_ids"]:
        for level in ("2", "3"):
            hit = firsts[fid].get(level)
            signals.append(signal(f"{names.get(fid, fid)} {fr.LEVELS[int(level)]} 이상", hit["at"] if hit else None,
                                  {"facility_id": fid, "why": hit["why"] if hit else None, "driver": hit["driver"] if hit else None}))
    for level in ("2", "3"):
        hit = region_first.get(level)
        signals.append(signal(f"{spec['region']} 시설 중 첫 {fr.LEVELS[int(level)]} 이상", hit["at"] if hit else None,
                              {"first_facility": hit["first_facility"] if hit else None, "why": hit["why"] if hit else None}))
    return {
        "id": spec["id"], "title": spec["title"], "region": spec["region"], "gauge": spec["gauge"],
        "window": {"start": spec["start"], "end": spec["end"], "step_min": STEP_MINUTES},
        "reference": {**ref, "precision_ko": PRECISION_KO[ref["precision"]]},
        "signals": signals, "region_at_reference": region_at_reference, "timeline": timeline,
    }


def build() -> dict[str, Any]:
    cases = [compute(spec["id"]) for spec in CASES]
    return {"built_at": datetime.now().isoformat(timespec="seconds"), "step_min": STEP_MINUTES,
            "rule": "facility_risk: 하천형 = 연결 관측소 단계 + 공식 특보 하한, 내수형 = 10 km 안 강우 1·3·12시간 누적(기상청 호우특보 기준량)",
            "cases": cases,
            "limitations": ["통제 시각은 보도 기준이다. 분 단위 기록은 오송(감찰 결과)뿐이고, 대전은 «경»·보도 시각 상한이다.",
                            "재생 수위·강우는 저장 1시간 자료다(오송 미호천교만 10분). 10분 간격 재생이어도 값은 시간 단위로 바뀐다.",
                            "통제를 앞선 신호라도 그 시각에 같은 지역의 다른 시설도 함께 올라갔다면 선별력은 낮다. region_at_reference를 함께 본다."]}


def scorecard(case_id: str | None = None) -> dict[str, Any]:
    """The stored scorecard (build_case_validation.py), optionally one case without its timeline."""
    if not SCORECARD_FILE.exists():
        raise FileNotFoundError("case scorecard not built: python data/scripts/build_case_validation.py")
    data = json.loads(SCORECARD_FILE.read_text(encoding="utf-8"))
    if case_id is None:
        return {**data, "cases": [{k: v for k, v in item.items() if k != "timeline"} for item in data["cases"]]}
    for item in data["cases"]:
        if item["id"] == case_id:
            return {**item, "built_at": data["built_at"], "limitations": data["limitations"]}
    raise ValueError(f"unknown validation case: {case_id}")

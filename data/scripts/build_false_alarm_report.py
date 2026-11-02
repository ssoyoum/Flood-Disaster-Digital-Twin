"""Build the 침수 헛울림 검증 리포트 table skeleton (기획 2, 대표 승인 2026-11-02 02:37).

Reads the validated cases from `case_scorecard.json` (already sourced: news report or
국무조정실 감찰 결과) as 확인 rows, and lists not-yet-confirmed incidents by hand as
미확인/보류 rows. The false-alarm ratio only counts 확인 rows; 미확인·보류 rows are
reported but excluded from the ratio so an unconfirmed case cannot silently count as
"not a false alarm".

Run: python data/scripts/build_false_alarm_report.py
Writes: data/processed/validation/false_alarm_report.json, docs/submission/false-alarm-verification-report.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_FILE = REPO_ROOT / "data" / "processed" / "validation" / "case_scorecard.json"
JSON_OUT = REPO_ROOT / "data" / "processed" / "validation" / "false_alarm_report.json"
MD_OUT = REPO_ROOT / "docs" / "submission" / "false-alarm-verification-report.md"

CONTROL_LABEL = {"control": "통제함", "inflow": "통제 안 함(유입)"}

# 아직 공식 출처로 확인되지 않은 사건은 여기 손으로 적는다. 확인되면 case_scorecard.json
# (CASES in backend/app/case_validation.py)로 옮기고 여기서 지운다.
PENDING_CASES: list[dict[str, Any]] = [
    {
        "id": "gungpyeong2-2025-07-17",
        "title": "오송 궁평2지하차도 2025-07-17",
        "date": "2025-07-17",
        "facility": "궁평2지하차도",
        "region": "충북",
        "confirm_status": "미확인",
        "control_status": None,
        "false_alarm": "판정 보류",
        "source": None,
        "note": "실제 통제 여부 확인 필요 → 충북도로관리사업소 확인 대기 중(TODO.md 0번 항목). 대표님 확인 필요.",
        "needs_ceo_confirmation": True,
    },
]


def load_confirmed_rows() -> list[dict[str, Any]]:
    if not SCORECARD_FILE.exists():
        raise FileNotFoundError(f"case scorecard not built: {SCORECARD_FILE}")
    data = json.loads(SCORECARD_FILE.read_text(encoding="utf-8"))
    rows = []
    for item in data["cases"]:
        ref = item["reference"]
        rows.append({
            "id": item["id"],
            "title": item["title"],
            "date": ref["at"][:10],
            "facility": item["title"].split(" 20")[0].split(" ", 1)[1] if " " in item["title"] else item["title"],
            "region": item["region"],
            "confirm_status": "확인",
            "control_status": CONTROL_LABEL.get(ref["kind"], ref["kind"]),
            "false_alarm": "아니오",
            "source": ref["source"],
            "note": ref["label"],
            "needs_ceo_confirmation": False,
        })
    return rows


def build() -> dict[str, Any]:
    rows = load_confirmed_rows() + PENDING_CASES
    rows.sort(key=lambda r: r["date"])
    confirmed = [r for r in rows if r["confirm_status"] == "확인"]
    unconfirmed = [r for r in rows if r["confirm_status"] != "확인"]
    false_alarms = [r for r in confirmed if r["false_alarm"] == "예"]
    ratio = (len(false_alarms) / len(confirmed)) if confirmed else None
    return {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "rule": "헛울림 비율 = 확인된 사건 중 헛울림(예) 건수 / 확인된 사건 전체 건수. 미확인·보류 사건은 분모에서 제외한다.",
        "counts": {
            "확인": len(confirmed),
            "미확인": len(unconfirmed),
            "헛울림(확인 사건 중)": len(false_alarms),
        },
        "false_alarm_ratio": ratio,
        "cases": rows,
    }


def to_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    ratio = report["false_alarm_ratio"]
    ratio_text = f"{ratio:.0%}" if ratio is not None else "계산 불가(확인된 사건 0건)"
    lines = [
        "# 침수 헛울림 검증 리포트",
        "",
        f"> 생성 시각: {report['built_at']} · 기획 2(대표 승인 2026-11-02 02:37) 1단계 표 틀",
        "",
        f"**확인 {counts['확인']}건 / 미확인 {counts['미확인']}건** · 헛울림 비율(확인 사건 기준) **{ratio_text}**"
        f" ({counts['헛울림(확인 사건 중)']}/{counts['확인']}건)",
        "",
        "미확인·보류 사건은 비율 계산에서 제외했다. 확인 상태가 바뀌면 이 표를 다시 생성한다.",
        "",
        "| 날짜 | 지점 | 지역 | 확인 상태 | 실제 통제 여부 | 헛울림 여부 | 근거 | 비고 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["cases"]:
        control = row["control_status"] or "-"
        source = row["source"] or "-"
        note = row["note"]
        if row.get("needs_ceo_confirmation"):
            note = f"**[대표님 확인 필요]** {note}"
        lines.append(
            f"| {row['date']} | {row['facility']} | {row['region']} | {row['confirm_status']} | "
            f"{control} | {row['false_alarm']} | {source} | {note} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    report = build()
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text(to_markdown(report), encoding="utf-8")
    print(f"확인 {report['counts']['확인']}건 / 미확인 {report['counts']['미확인']}건")
    print(f"-> {JSON_OUT}")
    print(f"-> {MD_OUT}")


if __name__ == "__main__":
    main()

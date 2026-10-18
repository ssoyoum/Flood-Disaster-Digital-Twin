"""Catalogue the 민관협력 지원 플랫폼(digitalsolveup.kr) datasets FloodOps can use, and which key each needs.

The platform's public list endpoint returns all 609 crisis datasets with their social-issue category. The
platform describes each dataset (request/response spec) but the calls go to the original provider, so each
needs that provider's key: HRFCO, data.go.kr, 서울 열린데이터광장 or the platform account itself (NIA).

    python data/scripts/collect_platform_catalog.py

Outputs:
- data/raw/platform/catalog.json, data/raw/platform/detail_{id}.json   (gitignored)
- data/processed/platform/flood_catalog.csv   flood-related datasets with the key they need and FloodOps' use
"""

from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "platform"
OUT = ROOT / "data" / "processed" / "platform" / "flood_catalog.csv"
API = "https://digitalsolveup.kr/api/v1/public-data/data"
KEYWORDS = ("하천", "수위", "강우", "강수", "침수", "홍수", "지하차도", "댐", "재해", "레이더", "특보", "펌프", "인명피해", "초단기")

# What FloodOps would do with a dataset (title substring → (use, priority 1–3)). Unlisted flood datasets get priority 3.
USES = {
    "레이터강수량(전국)": ("내수형 실시간 강우(레이더 격자) — 관측소 사이 빈 곳 보완", 1),
    "레이더강수량(지역)": ("내수형 실시간 강우(지역 레이더)", 2),
    "레이더강수영역": ("강수 영역 — 비 오는 시설 선별", 2),
    "기상특보 조회서비스_특보현황조회": ("호우특보 발효 구역을 시설 위험에 표시", 1),
    "기상특보 조회서비스": ("호우특보 발효 구역", 1),
    "초단기예보조회": ("향후 6시간 강수 예보 — 내수형 선행 시간", 1),
    "홍수예보발령": ("공식 홍수특보 발령 시각 — 규칙과 비교(HRFCO 키로 수집 중)", 1),
    "실시간 수위": ("하천형 판정(이미 HRFCO 일괄 API로 사용)", 3),
    "실시간 강수량": ("강우(이미 HRFCO 일괄 API로 사용)", 3),
    "실시간 댐자료": ("댐 방류 — 하천변 출입구 규칙(춘천 의암댐 2,000톤/s 사례)", 2),
    "다목적댐 운영 정보": ("댐 방류량 — 하천변 출입구 규칙", 2),
    "우량수위 관측정보": ("K-water 우량·수위 — HRFCO 밖 관측소 보완", 2),
    "주요도로 침수 정보": ("도로 침수 센서 14곳 — 내수형 강우 기준 채점(정답 자료)", 1),
    "실시간 강우량 정보": ("부산 강우 — 도로 침수 센서와 짝", 1),
    "배수펌프장 시설 현황": ("펌프 규모·유수지 용량 — 내수형 시설 용량", 1),
    "배수펌프장 정보": ("배수펌프장 위치·용량", 2),
    "배수펌프장 현황": ("배수펌프장 위치", 2),
    "하천 수위 현황": ("서울 하천 통제수위 — 하천변 출입구 기준 비교(정답 자료)", 1),
    "홍수관리구역": ("홍수관리구역 — 하천변 시설 범위", 2),
    "제방 및 호안": ("제방고 — 하천변 출입구 위험", 3),
    "인명피해 우려지역": ("인명피해 우려지역 통계 — 저지대 마을 대상 규모", 2),
    "재해위험지구": ("재해위험지구 — 저지대 마을 후보", 2),
    "침수 위험지역) 시공간": ("NIA 홍수경보·댐방류 융합 이벤트", 2),
    "침수흔적도": ("침수 흔적 — 내수형 검증 공간 자료", 2),
    "침수예상도": ("침수 예상 범위 — 시설 노출", 3),
    "상황전파메세지": ("재난 상황 전파 문자 — 운영 알림 비교", 2),
}


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def key_needed(agency: str, info: str, example: str) -> str:
    text = f"{agency} {info} {example}"
    if "한강홍수통제소" in agency or "HydroType" in example:
        return "HRFCO (있음)"
    if agency == "NIA" or "NIA" in info:
        return "플랫폼 계정 사용 신청"
    if "서울" in agency and ("openapi.seoul" in example or "START_INDEX" in example or "KEY" in example):
        return "서울 열린데이터광장"
    if "apihub.kma" in text:
        return "기상청 API 허브"
    return "data.go.kr"


def use_of(title: str) -> tuple[str, int]:
    for needle, value in USES.items():
        if needle in title:
            return value
    return ("참고", 3)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    catalog = get(f"{API}?page=1&size=1000")
    (RAW / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    rows = catalog["content"]
    picked = [r for r in rows if any(c["title"] == "홍수침수" for c in r.get("category", [])) or any(k in r["title"] for k in KEYWORDS)]
    out = []
    for row in picked:
        raw = RAW / f"detail_{row['id']}.json"
        if raw.exists():
            detail = json.loads(raw.read_text(encoding="utf-8"))
        else:
            detail = get(f"{API}/{row['id']}").get("content", {})
            raw.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
            time.sleep(0.1)
        example = re.sub(r"<[^>]+>", " ", html.unescape(detail.get("example") or ""))
        use, priority = use_of(row["title"])
        out.append({
            "priority": priority, "title": row["title"], "agency": row.get("agencyName") or "", "type": detail.get("type") or "",
            "format": detail.get("category") or "", "categories": ",".join(c["title"] for c in row.get("category", [])),
            "key_needed": key_needed(row.get("agencyName") or "", detail.get("infoSysName") or "", example),
            "floodops_use": use, "platform_id": row["id"],
        })
    out.sort(key=lambda r: (r["priority"], r["key_needed"], r["title"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)
    by_key: dict[str, int] = {}
    for r in out:
        if r["priority"] <= 2:
            by_key[r["key_needed"]] = by_key.get(r["key_needed"], 0) + 1
    print(f"catalog {len(rows)} · picked {len(picked)} · priority 1–2 by key: {by_key}")


if __name__ == "__main__":
    main()

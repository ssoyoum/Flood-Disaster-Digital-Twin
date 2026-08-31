import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed" / "osong"
VALIDATION_REPORT = PROCESSED / "validation_report.json"

DATASETS = {
    "DSSP-IF-10175": {
        "name": "damage_flood",
        "raw_dir": ROOT / "data" / "raw" / "damage_flood" / "osong" / "dssp_if_10175_pages",
        "status": "VERIFIED_SOURCE_ACQUIRED_NO_OSONG_2023_RECORD",
        "candidate_predicate": lambda record: str(record.get("MSTN_YR")) == "2023"
        and (
            str(record.get("RGN_CD", "")).startswith("43113")
            or str(record.get("DAM_RGN_DONG_CD", "")).startswith("43113")
        ),
        "validation": "DSSP-IF-10175 API source was acquired, but no 2023 Cheongju/Osong candidate records were present.",
        "data_warning": "Use this source as supporting inventory only unless a matching 2023 Osong event record is obtained.",
    },
    "DSSP-IF-10184": {
        "name": "relief_report",
        "raw_dir": ROOT / "data" / "raw" / "relief_report" / "osong" / "dssp_if_10184_pages",
        "status": "VERIFIED_SOURCE_ACQUIRED_CHEONGJU_2023_OSONG_TEXT_HITS",
        "candidate_predicate": lambda record: str(record.get("MSTN_YR")) == "2023"
        and str(record.get("STDG_CD", "")).startswith("4311")
        and str(record.get("DAM_DT", "")).startswith("202307"),
        "validation": "DSSP-IF-10184 API source was acquired and contains Cheongju July 2023 relief-report records, including Osong textual references.",
        "data_warning": "This is report/statistical text data, not Flood Extent geometry. Use it for event damage/evacuation interpretation.",
    },
}

TEXT_FIELDS = ["DAM_CS_CN", "EVPE_DSSTR_ETC", "SLGN_ACTV_STTS_ETC", "UTRH_STTS_ETC"]
OSONG_TERMS = ["오송", "궁평", "미호", "흥덕", "탑연"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_dataset(dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    pages = []
    records: list[dict[str, Any]] = []
    for path in sorted(spec["raw_dir"].glob("*.json")):
        payload = json.loads(path.read_bytes().decode("utf-8"))
        page_records = payload.get("body") or []
        pages.append(
            {
                "local_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "raw_size_bytes": path.stat().st_size,
                "raw_sha256": sha256(path),
                "result_code": payload.get("header", {}).get("resultCode"),
                "page_no": payload.get("pageNo"),
                "num_of_rows": payload.get("numOfRows"),
                "total_count": payload.get("totalCount"),
                "record_count": len(page_records),
            }
        )
        records.extend(page_records)

    candidates = [record for record in records if spec["candidate_predicate"](record)]
    if spec["name"] == "relief_report":
        for record in candidates:
            text = " ".join(str(record.get(field, "")) for field in TEXT_FIELDS)
            record["osong_text_hit"] = any(term in text for term in OSONG_TERMS)
            record["osong_search_terms"] = [term for term in OSONG_TERMS if term in text]
    year_counts = Counter(str(record.get("MSTN_YR")) for record in records)
    plus_one_year_count = sum(1 for record in records if str(record.get("MSTN_YR")) == "2024")
    output = PROCESSED / f"osong_{spec['name']}_2023_candidates.json"
    output.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    osong_text_hit_count = sum(1 for record in candidates if record.get("osong_text_hit"))
    return {
        "source": "Ministry of the Interior and Safety / Disaster Safety Data Sharing Platform",
        "dataset_id": dataset_id,
        "source_url": f"https://www.safetydata.go.kr/V2/api/{dataset_id}",
        "status": spec["status"],
        "raw_page_count": len(pages),
        "raw_record_count": len(records),
        "api_reported_total_count": pages[0]["total_count"] if pages else None,
        "raw_pages": pages,
        "year_counts": dict(sorted(year_counts.items())),
        "plus_one_year_2024_record_count": plus_one_year_count,
        "cheongju_sgg_code": "43113",
        "cheongju_stdg_code_prefix": "4311" if spec["name"] == "relief_report" else None,
        "osong_2023_candidate_record_count": len(candidates),
        "osong_text_hit_record_count": osong_text_hit_count if spec["name"] == "relief_report" else None,
        "processed_candidate_file": str(output.relative_to(ROOT)).replace("\\", "/"),
        "processed_candidate_sha256": sha256(output),
        "validation": spec["validation"],
        "data_warning": spec["data_warning"],
    }


def main() -> None:
    results = {spec["name"]: validate_dataset(dataset_id, spec) for dataset_id, spec in DATASETS.items()}
    report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    report["dssp_if_10175_damage_flood"] = results["damage_flood"]
    report["dssp_if_10184_relief_report"] = results["relief_report"]
    VALIDATION_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

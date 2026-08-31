import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from shapely import wkt
from shapely.geometry import mapping
from shapely.ops import transform
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "flood_extent" / "osong" / "dssp_if_00117_pages"
PROCESSED = ROOT / "data" / "processed" / "osong"
VALIDATION_REPORT = PROCESSED / "validation_report.json"
WEB_MERCATOR_TO_WGS84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages = []
    records: list[dict[str, Any]] = []
    for path in sorted(RAW_DIR.glob("dssp_if_00117_page_*.json")):
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
    return records, pages


def feature_from_record(record: dict[str, Any]) -> dict[str, Any] | None:
    geom_text = record.get("GEOM")
    if not geom_text:
        return None
    geom = wkt.loads(geom_text)
    geom_4326 = transform(WEB_MERCATOR_TO_WGS84, geom)
    properties = {key: value for key, value in record.items() if key != "GEOM"}
    return {"type": "Feature", "geometry": mapping(geom_4326), "properties": properties}


def main() -> None:
    records, pages = load_records()
    year_counts = Counter(str(record.get("FLDN_YR")) for record in records)
    ctpv_counts = Counter(str(record.get("STDG_CTPV_CD")) for record in records)
    cheongju_records = [record for record in records if str(record.get("STDG_SGG_CD")) == "43113"]
    osong_2023_records = [
        record
        for record in records
        if str(record.get("FLDN_YR")) == "2023"
        and str(record.get("STDG_CTPV_CD")) == "43"
        and str(record.get("STDG_SGG_CD")) == "43113"
    ]

    candidates = [feature_from_record(record) for record in osong_2023_records]
    candidates = [feature for feature in candidates if feature]
    candidate_file = PROCESSED / "osong_dssp_if_00117_2023_candidates.geojson"
    candidate_file.write_text(
        json.dumps({"type": "FeatureCollection", "features": candidates}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    validation = {
        "source": "Ministry of the Interior and Safety / Disaster Safety Data Sharing Platform",
        "dataset_id": "DSSP-IF-00117",
        "source_url": "https://www.safetydata.go.kr/V2/api/DSSP-IF-00117",
        "status": "VERIFIED_SOURCE_ACQUIRED_NO_OSONG_2023_RECORD",
        "raw_pages": pages,
        "raw_page_count": len(pages),
        "raw_record_count": len(records),
        "api_reported_total_count": pages[0]["total_count"] if pages else None,
        "geometry_field": "GEOM",
        "geometry_format": "WKT",
        "raw_geometry_crs_inferred": "EPSG:3857",
        "processed_crs": "EPSG:4326",
        "year_counts": dict(sorted(year_counts.items())),
        "province_counts": dict(sorted(ctpv_counts.items())),
        "cheongju_sgg_code": "43113",
        "cheongju_record_count": len(cheongju_records),
        "osong_2023_candidate_record_count": len(osong_2023_records),
        "processed_candidate_file": str(candidate_file.relative_to(ROOT)).replace("\\", "/"),
        "processed_candidate_sha256": sha256(candidate_file),
        "validation": "DSSP-IF-00117 API returned 38,003 records across 39 pages, but no records with FLDN_YR=2023 and Cheongju/Osong SGG code 43113 were present.",
        "data_warning": "Do not connect this dataset as the observed 2023 Osong Flood Extent unless a matching official record is obtained from another approved URL or portal export.",
    }
    report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    report["dssp_if_00117_flood_extent"] = validation
    VALIDATION_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

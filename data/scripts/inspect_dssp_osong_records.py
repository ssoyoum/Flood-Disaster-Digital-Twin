import json
from collections import Counter
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


ROOT = Path(__file__).resolve().parents[2]
OSONG_BBOX = (127.27, 36.58, 127.40, 36.68)
SEARCH_TERMS = ["오송", "궁평", "미호", "청주", "흥덕", "강내", "탑연", "지하차도", "미호강", "미호천"]
CODE_TERMS = ["43113", "43113250", "33043110", "33043"]

DATASETS = {
    "DSSP-IF-00117": {
        "name": "flood_extent",
        "path": ROOT / "data/raw/flood_extent/osong/dssp_if_00117_pages",
        "page_glob": "*.json",
        "year_field": "FLDN_YR",
        "region_fields": ["STDG_CTPV_CD", "STDG_SGG_CD"],
        "date_fields": ["FLDN_BGNG_YMD", "FLDN_END_YMD"],
        "text_fields": ["FLDN_DST_NM", "FLDN_CS_DTL_NM"],
        "geometry_field": "GEOM",
    },
    "DSSP-IF-10175": {
        "name": "damage_flood",
        "path": ROOT / "data/raw/damage_flood/osong/dssp_if_10175_pages",
        "page_glob": "*.json",
        "year_field": "MSTN_YR",
        "region_fields": ["RGN_CD", "DAM_RGN_DONG_CD", "DAM_RGN_STDG_CD"],
        "date_fields": ["DMG_YMD", "FLDN_BGNG_YMD", "FLSU_EXPC_YMD"],
        "text_fields": ["DAM_RGN_DADDR", "DAM_RGN_RONA_DADDR"],
        "geometry_field": None,
    },
    "DSSP-IF-10184": {
        "name": "relief_report",
        "path": ROOT / "data/raw/relief_report/osong/dssp_if_10184_pages",
        "page_glob": "*.json",
        "year_field": "MSTN_YR",
        "region_fields": ["STDG_CD"],
        "date_fields": ["DAM_DT"],
        "text_fields": ["DAM_CS_CN", "EVPE_DSSTR_ETC", "SLGN_ACTV_STTS_ETC", "UTRH_STTS_ETC"],
        "geometry_field": None,
    },
}


def fix_mojibake(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for page in sorted(path.glob("*.json")):
        payload = json.loads(page.read_bytes().decode("utf-8"))
        for record in payload.get("body") or []:
            records.append(record)
    return records


def in_bbox(geom: BaseGeometry) -> bool:
    minx, miny, maxx, maxy = geom.bounds
    bx1, by1, bx2, by2 = OSONG_BBOX
    return not (maxx < bx1 or minx > bx2 or maxy < by1 or miny > by2)


def geometry_candidates(records: list[dict[str, Any]], geometry_field: str) -> dict[str, Any]:
    transformers = {
        "EPSG:3857": Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform,
        "EPSG:5179": Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True).transform,
        "EPSG:5186": Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True).transform,
    }
    result: dict[str, Any] = {}
    for crs, transformer in transformers.items():
        hits = []
        for record in records:
            geom_text = record.get(geometry_field)
            if not geom_text:
                continue
            try:
                geom = transform(transformer, wkt.loads(geom_text))
            except Exception:
                continue
            if in_bbox(geom):
                hits.append(record)
        result[crs] = {
            "bbox_intersection_count": len(hits),
            "year_counts": dict(Counter(str(hit.get("FLDN_YR")) for hit in hits).most_common(20)),
            "sample": summarize_records(hits[:5], DATASETS["DSSP-IF-00117"]),
        }
    return result


def summarize_records(records: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    fields = []
    for key in [spec["year_field"], *spec["region_fields"], *spec["date_fields"], *spec["text_fields"]]:
        if key and key not in fields:
            fields.append(key)
    summary = []
    for record in records:
        summary.append({key: fix_mojibake(record.get(key)) for key in fields if key in record})
    return summary


def inspect_dataset(dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    records = load_records(spec["path"])
    year_counts = Counter(str(record.get(spec["year_field"])) for record in records)
    field_names = sorted(records[0].keys()) if records else []

    keyword_hits = []
    code_hits = []
    july_2023_hits = []
    for record in records:
        fixed_text = " ".join(str(fix_mojibake(record.get(field, ""))) for field in field_names)
        raw_text = " ".join(str(record.get(field, "")) for field in field_names)
        if any(term in fixed_text or term in raw_text for term in SEARCH_TERMS):
            keyword_hits.append(record)
        if any(term in raw_text or term in fixed_text for term in CODE_TERMS):
            code_hits.append(record)
        if any(str(record.get(field, "")).startswith("202307") for field in spec["date_fields"]):
            july_2023_hits.append(record)

    result = {
        "dataset_id": dataset_id,
        "record_count": len(records),
        "field_count": len(field_names),
        "fields": field_names,
        "year_field": spec["year_field"],
        "year_counts_top": dict(year_counts.most_common(30)),
        "region_fields": spec["region_fields"],
        "date_fields": spec["date_fields"],
        "text_fields": spec["text_fields"],
        "keyword_hit_count": len(keyword_hits),
        "keyword_hit_year_counts": dict(Counter(str(record.get(spec["year_field"])) for record in keyword_hits).most_common(20)),
        "keyword_hit_samples": summarize_records(keyword_hits[:10], spec),
        "code_hit_count": len(code_hits),
        "code_hit_year_counts": dict(Counter(str(record.get(spec["year_field"])) for record in code_hits).most_common(20)),
        "code_hit_samples": summarize_records(code_hits[:10], spec),
        "july_2023_hit_count": len(july_2023_hits),
        "july_2023_samples": summarize_records(july_2023_hits[:10], spec),
    }
    if spec["geometry_field"]:
        result["geometry_field"] = spec["geometry_field"]
        result["geometry_bbox_tests"] = geometry_candidates(records, spec["geometry_field"])
    return result


def main() -> None:
    results = {dataset_id: inspect_dataset(dataset_id, spec) for dataset_id, spec in DATASETS.items()}
    output = ROOT / "data/processed/osong/dssp_osong_record_inspection.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

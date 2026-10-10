"""Acquire public underpass inventories and export a catalogue, not an operational registry.

python data/scripts/collect_underpass_catalog.py --download
python data/scripts/collect_underpass_catalog.py
Raw source files remain local under data/raw/facilities; exports preserve overlapping records.
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/facilities"
OUT = ROOT / "data/processed/facilities"
SOURCES = ("15124755", "15045183", "15119688", "3080197")


def metadata(page):
    for block in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        value = json.loads(html.unescape(block))
        if value.get("@type") == "Dataset":
            return value
    raise ValueError("Missing Dataset metadata")


def decode_csv(blob):
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return blob.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Unsupported CSV encoding")


def first(row, *names):
    return next((row[name].strip() for name in names if row.get(name)), "")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Refresh public metadata and CSV files without credentials")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.download:
        import httpx
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for dataset_id in SOURCES:
                page = client.get(f"https://www.data.go.kr/data/{dataset_id}/fileData.do")
                page.raise_for_status()
                meta = metadata(page.text)
                url = next(item["contentUrl"] for item in meta["distribution"] if item["encodingFormat"] == "CSV")
                blob = client.get(url)
                blob.raise_for_status()
                if "html" in blob.headers.get("content-type", "").lower():
                    raise ValueError("Download returned HTML instead of CSV")
                decode_csv(blob.content)
                (RAW / f"{dataset_id}.html").write_text(page.text, encoding="utf-8")
                (RAW / f"{dataset_id}.csv").write_bytes(blob.content)
    inventory, sources = [], []
    for dataset_id in SOURCES:
        page_path, raw_path = RAW / f"{dataset_id}.html", RAW / f"{dataset_id}.csv"
        meta = metadata(page_path.read_text(encoding="utf-8"))
        blob = raw_path.read_bytes()
        content, encoding = decode_csv(blob)
        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames
        rows = list(reader)
        title = re.search(r"<title>(.*?)</title>", page_path.read_text(encoding="utf-8"), re.S)
        dated = re.search(r"_(\d{8})", html.unescape(title.group(1))) if title else None
        for number, row in enumerate(rows, 1):
            name = first(row, "시설물명", "시설명", "지하차도명")
            if not name:
                raise ValueError(f"Missing name in {dataset_id} row {number}")
            location = first(row, "주소", "위치") or " ".join(filter(None, (first(row, "시도"), first(row, "시군구"))))
            inventory.append({
                "source_record_id": f"{dataset_id}:{number}", "dataset_id": dataset_id,
                "source_ordinal": first(row, "순번(No)"), "name": name, "location_raw": location,
                "management_category": first(row, "관리주체구분"), "agency_raw": first(row, "기관구분"),
                "structure_raw": first(row, "항목명"), "length_raw": first(row, "총길이(미터)", "총길이", "총연장(미터)"),
                "width_raw": first(row, "총폭(미터)", "총폭", "폭(미터)"), "height_raw": first(row, "높이(미터)", "높이", "통과높이"),
                "latitude": "", "longitude": "", "driver": "unverified", "gauge_station_id": "",
                "status": "CATALOG_ONLY", "source_date": dated.group(1) if dated else "",
                "source_updated_at": meta.get("dateModified", ""), "source_url": meta["url"],
                "source_attributes_json": json.dumps(row, ensure_ascii=False),
            })
        sources.append({
            "dataset_id": dataset_id, "title": meta["name"], "source_url": meta["url"],
            "source_date": dated.group(1) if dated else None, "source_updated_at": meta.get("dateModified"),
            "raw_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "raw_sha256": hashlib.sha256(blob).hexdigest(), "encoding": encoding,
            "downloaded_at": datetime.fromtimestamp(raw_path.stat().st_mtime, timezone(timedelta(hours=9))).isoformat(),
            "row_count": len(rows), "columns": headers,
            "license": meta.get("license"), "coordinate_fields": [name for name in headers if any(word in name for word in ("위도", "경도", "좌표"))],
        })
    assert len({row["source_record_id"] for row in inventory}) == len(inventory)
    candidates = [row for row in inventory if row["dataset_id"] == "15124755" and "충청북도" in row["location_raw"]]
    write_csv(OUT / "underpass_inventory.csv", inventory)
    write_csv(OUT / "chungbuk_underpass_candidates.csv", candidates)
    manifest = {
        "schema_version": "1.0", "checked_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "record_count": len(inventory), "chungbuk_national_source_records": len(candidates),
        "status": "CATALOG_ONLY", "operational_facilities_added": 0,
        "deduplication": "No cross-source or same-name merging; record count is not a unique facility count.",
        "limits": ["The national inventory covers facilities subject to the Facility Safety Act, not all underpasses.",
                   "Missing coordinates, sensors, closure histories and approved control rules remain unknown.",
                   "Structural safety grades are not flood-risk grades; nearest gauge is not automatically representative."],
        "sources": sources,
    }
    (ROOT / "data/manifests/underpass-catalog.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(inventory), "chungbuk_candidates": len(candidates), "operational_facilities_added": 0}))


if __name__ == "__main__":
    main()

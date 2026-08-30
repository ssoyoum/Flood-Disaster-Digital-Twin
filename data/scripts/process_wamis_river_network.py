"""Acquire WAMIS river-network SHP files and clip them to an event AOI.

Raw ZIP files are preserved under data/raw. Processed GeoJSON outputs are
written under data/processed/<event_slug>/ in EPSG:4326.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "river" / "wamis_river_network"
DATA_FILES_URL = "https://www.wamis.go.kr/main/data_files.do"
DOWNLOAD_URL = "https://www.wamis.go.kr/main/download.do"
PDSSN = "621"
FILES = {
    "national": "ntn_rvr.zip",
    "local": "lcl_rvr.zip",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def download_file(server_filename: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    params = urllib.parse.urlencode({"pdssn": PDSSN, "fileName": server_filename})
    request = urllib.request.Request(f"{DOWNLOAD_URL}?{params}", headers={"User-Agent": "FloodOps/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        output.write_bytes(response.read())
    if output.stat().st_size == 0:
        raise RuntimeError(f"Downloaded empty WAMIS file: {output}")


def read_layer(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:5179")
    return gdf


def clip_to_bbox(gdf: gpd.GeoDataFrame, bbox_wgs84: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    aoi = gpd.GeoSeries([box(*bbox_wgs84)], crs="EPSG:4326").to_crs(gdf.crs)
    subset = gdf[gdf.intersects(aoi.iloc[0])].copy()
    if subset.empty:
        return gpd.GeoDataFrame(subset, geometry="geometry", crs=gdf.crs).to_crs("EPSG:4326")
    return gpd.clip(subset, aoi).to_crs("EPSG:4326")


def process(event_slug: str, bbox: tuple[float, float, float, float], force_download: bool) -> dict:
    processed_dir = ROOT / "data" / "processed" / event_slug
    processed_dir.mkdir(parents=True, exist_ok=True)

    outputs = []
    report = {
        "source": "WAMIS river network",
        "pdssn": PDSSN,
        "aoi_bbox": list(bbox),
        "raw_files": {},
        "processed_files": {},
    }

    for scope, filename in FILES.items():
        raw_path = RAW_DIR / filename
        if force_download or not raw_path.exists():
            download_file(filename, raw_path)

        source = read_layer(raw_path)
        clipped = clip_to_bbox(source, bbox)
        clipped["source_dataset"] = "WAMIS river network"
        clipped["river_scope"] = scope
        clipped["data_role"] = "official_river_polygon_context"
        clipped["aoi_bbox"] = ",".join(str(value) for value in bbox)

        output = processed_dir / f"{event_slug}_wamis_{scope}_rivers.geojson"
        clipped.to_file(output, driver="GeoJSON")
        outputs.append(clipped)

        report["raw_files"][scope] = {
            "local_file": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": raw_path.stat().st_size,
            "sha256": sha256(raw_path),
            "feature_count": int(len(source)),
            "geometry_type": " / ".join(sorted(source.geom_type.dropna().unique())),
            "crs": source.crs.to_string() if source.crs else "UNKNOWN",
        }
        report["processed_files"][scope] = {
            "local_file": str(output.relative_to(ROOT)).replace("\\", "/"),
            "feature_count": int(len(clipped)),
            "geometry_type": " / ".join(sorted(clipped.geom_type.dropna().unique())),
            "crs": clipped.crs.to_string() if clipped.crs else "UNKNOWN",
            "sha256": sha256(output),
        }

    combined = gpd.GeoDataFrame(pd.concat(outputs, ignore_index=True), crs="EPSG:4326")
    combined_output = processed_dir / f"{event_slug}_wamis_rivers.geojson"
    combined.to_file(combined_output, driver="GeoJSON")
    report["processed_files"]["combined"] = {
        "local_file": str(combined_output.relative_to(ROOT)).replace("\\", "/"),
        "feature_count": int(len(combined)),
        "geometry_type": " / ".join(sorted(combined.geom_type.dropna().unique())),
        "crs": combined.crs.to_string(),
        "sha256": sha256(combined_output),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-slug", default="osong")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"), required=True)
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    report = process(args.event_slug, tuple(args.bbox), args.force_download)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

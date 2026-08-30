"""Create Osong DEM context layers from the local Copernicus DEM tile.

This does not create a flood extent. It derives low-elevation terrain context
from the existing DEM using observed elevation percentiles inside the AOI.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import tifffile
from shapely.geometry import box


ROOT = Path(__file__).resolve().parents[2]
RAW_DEM = ROOT / "data" / "raw" / "copernicus_dem_glo30" / "Copernicus_DSM_COG_10_N36_00_E127_00_DEM.tif"
PROCESSED = ROOT / "data" / "processed" / "osong"
AOI_BBOX = (127.27, 36.58, 127.40, 36.68)
GRID_COLS = 40
GRID_ROWS = 32


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_dem_window() -> tuple[np.ndarray, tuple[float, float, float, float], dict]:
    with tifffile.TiffFile(RAW_DEM) as tif:
        page = tif.pages[0]
        scale = page.tags["ModelPixelScaleTag"].value
        tiepoint = page.tags["ModelTiepointTag"].value
        image = page.asarray()

    pixel_x, pixel_y = float(scale[0]), float(scale[1])
    origin_x, origin_y = float(tiepoint[3]), float(tiepoint[4])
    minx, miny, maxx, maxy = AOI_BBOX
    col0 = max(0, int(np.floor((minx - origin_x) / pixel_x)))
    col1 = min(image.shape[1], int(np.ceil((maxx - origin_x) / pixel_x)))
    row0 = max(0, int(np.floor((origin_y - maxy) / pixel_y)))
    row1 = min(image.shape[0], int(np.ceil((origin_y - miny) / pixel_y)))
    window = image[row0:row1, col0:col1].astype(float)
    bounds = (
        origin_x + col0 * pixel_x,
        origin_y - row1 * pixel_y,
        origin_x + col1 * pixel_x,
        origin_y - row0 * pixel_y,
    )
    metadata = {
        "raw_file": str(RAW_DEM.relative_to(ROOT)).replace("\\", "/"),
        "raw_sha256": sha256(RAW_DEM),
        "raw_crs": "EPSG:4326",
        "raw_pixel_size_degrees": [pixel_x, pixel_y],
        "raw_tile_shape": list(image.shape),
        "window_shape": list(window.shape),
        "window_bounds": list(bounds),
    }
    return window, bounds, metadata


def block_mean(values: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> float:
    block = values[y0:y1, x0:x1]
    finite = block[np.isfinite(block)]
    if finite.size == 0:
        return float("nan")
    return float(finite.mean())


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    dem, bounds, metadata = read_dem_window()
    finite = dem[np.isfinite(dem)]
    if finite.size == 0:
        raise ValueError("No valid DEM pixels found in Osong AOI")

    percentiles = {
        "p05": float(np.percentile(finite, 5)),
        "p10": float(np.percentile(finite, 10)),
        "p25": float(np.percentile(finite, 25)),
        "p50": float(np.percentile(finite, 50)),
        "p75": float(np.percentile(finite, 75)),
        "p90": float(np.percentile(finite, 90)),
        "p95": float(np.percentile(finite, 95)),
    }
    low_threshold = percentiles["p25"]

    minx, miny, maxx, maxy = AOI_BBOX
    dx = (maxx - minx) / GRID_COLS
    dy = (maxy - miny) / GRID_ROWS
    rows = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            cell_minx = minx + col * dx
            cell_maxx = minx + (col + 1) * dx
            cell_maxy = maxy - row * dy
            cell_miny = maxy - (row + 1) * dy

            y0 = int(row * dem.shape[0] / GRID_ROWS)
            y1 = max(y0 + 1, int((row + 1) * dem.shape[0] / GRID_ROWS))
            x0 = int(col * dem.shape[1] / GRID_COLS)
            x1 = max(x0 + 1, int((col + 1) * dem.shape[1] / GRID_COLS))
            elevation = block_mean(dem, y0, y1, x0, x1)
            if not np.isfinite(elevation):
                continue
            rows.append(
                {
                    "grid_id": f"dem-{row:02d}-{col:02d}",
                    "mean_elevation_m": round(elevation, 2),
                    "terrain_class": "LOW_ELEVATION_CONTEXT" if elevation <= low_threshold else "TERRAIN_CONTEXT",
                    "threshold_note": "LOW_ELEVATION_CONTEXT means <= AOI p25 elevation; it is not a flood extent.",
                    "geometry": box(cell_minx, cell_miny, cell_maxx, cell_maxy),
                }
            )

    grid = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    grid_file = PROCESSED / "osong_dem_elevation_grid.geojson"
    low_file = PROCESSED / "osong_dem_low_elevation_context.geojson"
    summary_file = PROCESSED / "osong_dem_summary.json"
    grid.to_file(grid_file, driver="GeoJSON")
    low = grid[grid["terrain_class"] == "LOW_ELEVATION_CONTEXT"].copy()
    low.to_file(low_file, driver="GeoJSON")

    summary = {
        **metadata,
        "aoi_bbox": list(AOI_BBOX),
        "source": "Copernicus DEM GLO-30",
        "source_type": "DEM",
        "status": "DERIVED",
        "role": "Terrain context only",
        "min_elevation_m": float(finite.min()),
        "max_elevation_m": float(finite.max()),
        "mean_elevation_m": float(finite.mean()),
        "percentiles_m": percentiles,
        "low_elevation_threshold_m": low_threshold,
        "grid_file": str(grid_file.relative_to(ROOT)).replace("\\", "/"),
        "grid_feature_count": int(len(grid)),
        "low_elevation_file": str(low_file.relative_to(ROOT)).replace("\\", "/"),
        "low_elevation_feature_count": int(len(low)),
        "grid_sha256": sha256(grid_file),
        "low_elevation_sha256": sha256(low_file),
        "data_warning": "This is terrain context, not observed inundation or modeled flood extent.",
    }
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

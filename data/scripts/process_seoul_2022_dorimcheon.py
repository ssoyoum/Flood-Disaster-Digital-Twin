"""Build the Seoul 2022 Dorimcheon reconstruction layers from local raw sources.

Inputs (kept outside Git, see .gitignore):
- data/raw/seoul_flood_footprints_2022/*.shp      Seoul official flood trace map 2022 (침수흔적도), EPSG:5179
- data/raw/seoul/osm_dorimcheon_2022-08-08.json    OSM Overpass attic snapshot at 2022-08-08T00:00:00Z
- data/processed/seoul_rainfall_2022_event.csv     Seoul 10-minute rain gauges, 2022-08-08..17
- AL_D010_11_20260809.zip                          VWorld GIS building integrated info, Seoul full snapshot
  (path from SEOUL_BUILDINGS_ZIP, default: sibling Basement-Flood-Vulnerability repository)

Street addresses are dropped from every output. The trace map and building register carry lot-level
addresses of private homes; the twin only needs district / dong level context.
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box, mapping

ROOT = Path(__file__).resolve().parents[2]
RAW_FOOTPRINT_DIR = ROOT / "data/raw/seoul_flood_footprints_2022"
RAW_OSM = ROOT / "data/raw/seoul/osm_dorimcheon_2022-08-08.json"
RAINFALL_CSV = ROOT / "data/processed/seoul_rainfall_2022_event.csv"
BUILDINGS_ZIP = Path(
    os.environ.get(
        "SEOUL_BUILDINGS_ZIP",
        ROOT.parent / "Basement-Flood-Vulnerability/data/raw/buildings/AL_D010_11_20260809.zip",
    )
)
OUT = ROOT / "data/processed/seoul_2022"

# Dorimcheon corridor: Sillim, Sindaebang, Daerim and the Dorimcheon main channel.
AOI_BOUNDS = (126.89, 37.465, 126.955, 37.51)
EVENT_DATE = "2022-08-08"
METRIC_CRS = "EPSG:5179"
GAUGES = ["신림P", "관악구청", "동작구청", "도림2동P", "구로구청", "영등포구청"]


def write_geojson(name: str, frame: gpd.GeoDataFrame) -> None:
    frame.to_crs("EPSG:4326").to_file(OUT / name, driver="GeoJSON", encoding="utf-8", COORDINATE_PRECISION=6)


def aoi_frame() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"name": ["도림천 유역 분석 범위"], "basis": ["bbox around Sillim, Sindaebang, Daerim and the Dorimcheon channel"]},
        geometry=[box(*AOI_BOUNDS)],
        crs="EPSG:4326",
    )


def process_footprints(aoi: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    source = glob.glob(str(RAW_FOOTPRINT_DIR / "*.shp"))[0]
    frame = gpd.read_file(source, encoding="cp949")
    frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty].copy()
    frame["geometry"] = frame.geometry.make_valid()
    frame = frame.to_crs("EPSG:4326")
    frame = frame[frame.intersects(aoi.geometry.iloc[0])].copy()
    district = frame["GU_NAM"].fillna("").str.strip()
    frame["district"] = district.where(district.str.endswith("구"), district + "구")
    out = gpd.GeoDataFrame(
        {
            "flood_depth_m": frame["F_SHIM"].astype(float),
            "flood_area_m2": frame["F_AREA"].astype(float),
            "district": frame["district"],
            "admin_code": frame["ADM_CD"],
            "damage_type": frame["TYPE"],
            "start_date": frame["F_SAT_YMD"],
            "end_date": frame["F_END_YMD"],
            "origin": "OBSERVED",
            "source": "서울시 침수흔적도 2022 (공공데이터포털 15133406)",
        },
        geometry=frame.geometry.values,
        crs="EPSG:4326",
    )
    out = out[out.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].reset_index(drop=True)
    out["trace_id"] = [f"trace-{index}" for index in range(len(out))]
    return out


def element_coords(element: dict) -> list[list[float]]:
    return [[point["lon"], point["lat"]] for point in element.get("geometry", [])]


def process_osm() -> dict[str, gpd.GeoDataFrame]:
    raw = json.loads(RAW_OSM.read_text(encoding="utf-8"))
    roads, waterways, facilities = [], [], []
    for element in raw["elements"]:
        tags = element.get("tags", {})
        coords = element_coords(element)
        name = tags.get("name") or tags.get("ref") or ""
        if tags.get("highway") and len(coords) >= 2:
            roads.append({"name": name, "highway": tags["highway"], "osm_id": element["id"], "geometry": {"type": "LineString", "coordinates": coords}})
        if tags.get("waterway") and len(coords) >= 2:
            waterways.append({"name": name, "waterway": tags["waterway"], "osm_id": element["id"], "geometry": {"type": "LineString", "coordinates": coords}})
        if tags.get("amenity"):
            if element.get("type") == "node":
                point = [element["lon"], element["lat"]]
            elif coords:
                point = [sum(item[0] for item in coords) / len(coords), sum(item[1] for item in coords) / len(coords)]
            else:
                continue
            facilities.append({"name": name, "amenity": tags["amenity"], "osm_id": element["id"], "geometry": {"type": "Point", "coordinates": point}})

    def frame(rows: list[dict]) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame.from_features(
            [{"type": "Feature", "properties": {k: v for k, v in row.items() if k != "geometry"} | {"origin": "OBSERVED"}, "geometry": row["geometry"]} for row in rows],
            crs="EPSG:4326",
        )

    return {"roads": frame(roads), "waterways": frame(waterways), "facilities": frame(facilities)}


def process_buildings(aoi: gpd.GeoDataFrame, traces: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    source = f"/vsizip/{BUILDINGS_ZIP.resolve()}/AL_D010_11_20260809.shp"
    bounds = aoi.to_crs("EPSG:5186").total_bounds
    frame = gpd.read_file(source, bbox=tuple(bounds), encoding="cp949").to_crs("EPSG:4326")
    frame = frame[frame.intersects(aoi.geometry.iloc[0])].copy()
    approval = pd.to_datetime(frame["A13"], errors="coerce")
    after_event = approval > pd.Timestamp(EVENT_DATE)
    stock = frame[~after_event].copy()
    stock_approval = approval[~after_event]

    metric = stock.to_crs(METRIC_CRS)
    trace_metric = traces[["flood_depth_m", "geometry"]].to_crs(METRIC_CRS)
    joined = gpd.sjoin(metric[["geometry"]], trace_metric, how="inner", predicate="intersects")
    max_depth = joined.groupby(level=0)["flood_depth_m"].max()
    trace_hits = joined.groupby(level=0).size()

    exposed = stock.loc[max_depth.index].copy()
    out = gpd.GeoDataFrame(
        {
            "building_id": exposed["A1"].astype(str),
            "dong": exposed["A4"],
            "main_use": exposed["A9"],
            "above_ground_floors": exposed["A26"],
            "underground_floors": exposed["A27"],
            "use_approval_date": exposed["A13"],
            "max_trace_depth_m": max_depth.loc[exposed.index].round(2).values,
            "trace_count": trace_hits.loc[exposed.index].values,
            "origin": "OBSERVED_OVERLAY",
            "source": "국토교통부 GIS건물통합정보 (2026-08-09 스냅샷, 사용승인일 2022-08-08 이전) x 서울시 침수흔적도 2022",
        },
        geometry=exposed.geometry.values,
        crs="EPSG:4326",
    ).reset_index(drop=True)

    residential_uses = {"단독주택", "공동주택"}
    stats = {
        "snapshot": "2026-08-09",
        "rows_in_aoi": int(len(frame)),
        "excluded_approved_after_event": int(after_event.sum()),
        "stock_at_event": int(len(stock)),
        "stock_missing_approval_date": int(stock_approval.isna().sum()),
        "stock_residential": int(stock["A9"].isin(residential_uses).sum()),
        "stock_with_underground_floors": int((pd.to_numeric(stock["A27"], errors="coerce") > 0).sum()),
        "trace_intersecting": int(len(out)),
        "trace_intersecting_residential": int(out["main_use"].isin(residential_uses).sum()),
        "trace_intersecting_with_underground_floors": int((pd.to_numeric(out["underground_floors"], errors="coerce") > 0).sum()),
        "trace_intersecting_depth_ge_0_5m": int((out["max_trace_depth_m"] >= 0.5).sum()),
        "trace_intersecting_by_use": {str(k): int(v) for k, v in out["main_use"].value_counts().head(8).items()},
    }
    return out, stats


def process_rainfall() -> tuple[pd.DataFrame, dict]:
    rain = pd.read_csv(RAINFALL_CSV, encoding="utf-8-sig", parse_dates=["observed_at"])
    rain = rain[rain["station_name"].isin(GAUGES)]
    rain = rain[(rain["observed_at"] >= "2022-08-08 00:00") & (rain["observed_at"] < "2022-08-10 00:00")].copy()
    rain = rain.sort_values(["station_name", "observed_at"])
    rain["rainfall_60min_mm"] = rain.groupby("station_name")["rainfall_10min_mm"].transform(lambda s: s.rolling(6, min_periods=6).sum()).round(1)
    peaks = {}
    for name, group in rain.groupby("station_name"):
        series = group.set_index("observed_at")
        day = series.loc["2022-08-08"]
        peak_at = series["rainfall_60min_mm"].idxmax()
        peaks[name] = {
            "station_code": str(group["station_code"].iloc[0]),
            "district": group["district_name"].iloc[0],
            "rows_0808_0809": int(len(group)),
            "total_0808_mm": round(float(day["rainfall_10min_mm"].sum()), 1),
            "max_60min_mm": float(series["rainfall_60min_mm"].max()),
            "max_60min_end": peak_at.strftime("%Y-%m-%dT%H:%M:00+09:00"),
        }
    output = rain[["station_code", "station_name", "district_name", "observed_at", "rainfall_10min_mm", "rainfall_60min_mm"]]
    return output, peaks


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    aoi = aoi_frame()
    traces = process_footprints(aoi)
    osm = process_osm()
    buildings, building_stats = process_buildings(aoi, traces)
    rainfall, rainfall_peaks = process_rainfall()

    write_geojson("seoul_dorimcheon_aoi.geojson", aoi)
    write_geojson("seoul_flood_traces_2022_dorimcheon.geojson", traces)
    write_geojson("seoul_osm_roads_2022.geojson", osm["roads"])
    write_geojson("seoul_osm_waterways_2022.geojson", osm["waterways"])
    write_geojson("seoul_osm_facilities_2022.geojson", osm["facilities"])
    write_geojson("seoul_buildings_trace_overlay_2022.geojson", buildings)
    rainfall.to_csv(OUT / "seoul_rainfall_dorimcheon_2022-08-08.csv", index=False, encoding="utf-8")

    aoi_metric = aoi.to_crs(METRIC_CRS).geometry.iloc[0]
    trace_metric = traces.to_crs(METRIC_CRS)
    trace_union = trace_metric.union_all()
    roads_metric = osm["roads"].to_crs(METRIC_CRS)
    depth = traces["flood_depth_m"]
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event_id": "seoul-2022",
        "aoi_bounds": list(AOI_BOUNDS),
        "aoi_area_km2": round(aoi_metric.area / 1e6, 3),
        "traces": {
            "count": int(len(traces)),
            "union_area_km2": round(trace_union.area / 1e6, 3),
            "union_area_in_aoi_km2": round(trace_union.intersection(aoi_metric).area / 1e6, 3),
            "depth_m": {"median": float(depth.median()), "p90": round(float(depth.quantile(0.9)), 2), "max": float(depth.max())},
            "depth_ge_0_5m": int((depth >= 0.5).sum()),
            "by_damage_type": {str(k): int(v) for k, v in traces["damage_type"].value_counts().items()},
            "by_district": {str(k): int(v) for k, v in traces["district"].value_counts().items()},
        },
        "buildings": building_stats,
        "roads": {
            "osm_road_km_in_aoi": round(roads_metric.intersection(aoi_metric).length.sum() / 1000, 1),
            "osm_road_km_in_traces": round(roads_metric.intersection(trace_union).length.sum() / 1000, 1),
            "osm_snapshot": "2022-08-08T00:00:00Z",
        },
        "rainfall_peaks": rainfall_peaks,
        "osm_counts": {key: int(len(value)) for key, value in osm.items()},
    }
    (OUT / "seoul_dorimcheon_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

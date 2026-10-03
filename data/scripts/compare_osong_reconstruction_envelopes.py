import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely import STRtree
from shapely.geometry import shape
from shapely.ops import transform, unary_union


REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"
APPROX_FILE = OSONG_DIR / "osong_approx_flood_envelope_timeline.geojson"
HAND_FILE = OSONG_DIR / "osong_hand_flood_envelope_timeline.geojson"
OUTPUT_FILE = OSONG_DIR / "osong_reconstruction_envelope_comparison.json"
AOI_FILE = OSONG_DIR / "osong_sgis_admin_boundary_2023.geojson"
BUILDINGS_FILE = OSONG_DIR / "osong_official_buildings_2023.geojson"
ROADS_FILE = OSONG_DIR / "osong_osm_roads_2023.geojson"

TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True).transform

STAGES = [
    "warning",
    "hydraulic_warning",
    "overtopping",
    "levee_failure",
    "underpass_inflow",
    "unsafe_driving",
    "full_inundation",
]


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_metric_geoms(path: Path) -> list:
    return [transform(TO_METERS, shape(feature["geometry"])) for feature in read_geojson(path).get("features", [])]


class OverlapContext:
    """AOI and inventory layers used to show how much of Osong-eup an envelope covers (DQ-008)."""

    def __init__(self) -> None:
        self.aoi = unary_union(read_metric_geoms(AOI_FILE))
        self.buildings = read_metric_geoms(BUILDINGS_FILE)
        self.roads = read_metric_geoms(ROADS_FILE)
        self.building_tree = STRtree(self.buildings)
        self.road_tree = STRtree(self.roads)
        self.road_length_km = sum(road.length for road in self.roads) / 1000
        # The inventories cover a bbox wider than Osong-eup, so shares use the in-AOI totals.
        self.aoi_building_count = len(self.building_tree.query(self.aoi, predicate="intersects"))
        self.aoi_road_km = self._road_km_inside(self.aoi)

    def _road_km_inside(self, area) -> float:
        return sum(self.roads[index].intersection(area).length for index in self.road_tree.query(area, predicate="intersects")) / 1000

    def summarize(self, envelope) -> dict[str, Any]:
        clipped = envelope.intersection(self.aoi)
        building_hits = len(self.building_tree.query(clipped, predicate="intersects")) if not clipped.is_empty else 0
        road_km = self._road_km_inside(clipped) if not clipped.is_empty else 0.0
        return {
            "aoi_clipped_area_km2": round(clipped.area / 1_000_000, 4),
            "aoi_clipped_share_pct": round(clipped.area / self.aoi.area * 100, 1),
            "buildings_intersecting": building_hits,
            "buildings_intersecting_pct": round(building_hits / self.aoi_building_count * 100, 1),
            "road_km_inside": round(road_km, 1),
            "road_km_inside_pct": round(road_km / self.aoi_road_km * 100, 1),
        }


def summarize_stage(data: dict[str, Any], stage: str) -> tuple[dict[str, Any], Any]:
    features = [
        feature
        for feature in data.get("features", [])
        if feature.get("geometry", {}).get("type") in {"Polygon", "MultiPolygon"}
        and feature.get("properties", {}).get("state") == stage
    ]
    geoms = [transform(TO_METERS, shape(feature["geometry"])) for feature in features]
    envelope = unary_union(geoms) if geoms else None
    area_km2 = envelope.area / 1_000_000 if envelope is not None else 0.0
    label = features[0]["properties"].get("label") if features else ""
    return {"feature_count": len(features), "area_km2": round(area_km2, 4), "label": label}, envelope


def main() -> None:
    approx = read_geojson(APPROX_FILE)
    hand = read_geojson(HAND_FILE)
    overlap = OverlapContext()
    rows = []
    for stage in STAGES:
        approx_summary, approx_envelope = summarize_stage(approx, stage)
        hand_summary, hand_envelope = summarize_stage(hand, stage)
        approx_area = approx_summary["area_km2"]
        hand_area = hand_summary["area_km2"]
        rows.append(
            {
                "stage": stage,
                "label": hand_summary["label"] or approx_summary["label"],
                "approx_features": approx_summary["feature_count"],
                "approx_area_km2": approx_area,
                "hand_features": hand_summary["feature_count"],
                "hand_area_km2": hand_area,
                "hand_minus_approx_area_km2": round(hand_area - approx_area, 4),
                "hand_to_approx_area_ratio": round(hand_area / approx_area, 2) if approx_area else None,
                "approx_aoi_overlap": overlap.summarize(approx_envelope) if approx_envelope is not None else None,
                "hand_aoi_overlap": overlap.summarize(hand_envelope) if hand_envelope is not None else None,
            }
        )

    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event_id": "osong-2023",
        "status": "TEMPORARY",
        "source_type": "DERIVED_COMPARISON",
        "role": "Compare old low-elevation approximation with HAND-like reconstruction.",
        "inputs": [
            str(APPROX_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(HAND_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(AOI_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(BUILDINGS_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(ROADS_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        ],
        "area_crs": "EPSG:5179",
        "aoi": {
            "area_km2": round(overlap.aoi.area / 1_000_000, 3),
            "official_buildings_in_aoi": overlap.aoi_building_count,
            "osm_road_km_in_aoi": round(overlap.aoi_road_km, 1),
            "inventory_note": f"Inventory files cover a wider bbox ({len(overlap.buildings)} buildings, {overlap.road_length_km:.1f} road km); overlap shares use in-AOI totals.",
        },
        "data_warning": [
            "Areas are method-comparison areas, not official inundation area.",
            "HAND uses relative water-level change and drainage-relative elevation, not absolute water-surface elevation.",
            "Do not use this comparison as exposure KPI evidence.",
            "AOI overlap counts show how much of Osong-eup an envelope covers (DQ-008); they are not affected-building or affected-road counts.",
        ],
        "methods": {
            "approx_flood_envelope": "Existing simple approximation using low-elevation DEM cells and distance thresholds.",
            "hand_reconstruction": "Improved HAND-like reconstruction using drainage-relative elevation, WAMIS connectivity, observed water-level rise, and timeline stages.",
        },
        "rows": rows,
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union


REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"
APPROX_FILE = OSONG_DIR / "osong_approx_flood_envelope_timeline.geojson"
HAND_FILE = OSONG_DIR / "osong_hand_flood_envelope_timeline.geojson"
OUTPUT_FILE = OSONG_DIR / "osong_reconstruction_envelope_comparison.json"

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


def summarize_stage(data: dict[str, Any], stage: str) -> dict[str, Any]:
    features = [
        feature
        for feature in data.get("features", [])
        if feature.get("geometry", {}).get("type") in {"Polygon", "MultiPolygon"}
        and feature.get("properties", {}).get("state") == stage
    ]
    geoms = [transform(TO_METERS, shape(feature["geometry"])) for feature in features]
    area_km2 = unary_union(geoms).area / 1_000_000 if geoms else 0.0
    label = features[0]["properties"].get("label") if features else ""
    return {"feature_count": len(features), "area_km2": round(area_km2, 4), "label": label}


def main() -> None:
    approx = read_geojson(APPROX_FILE)
    hand = read_geojson(HAND_FILE)
    rows = []
    for stage in STAGES:
        approx_summary = summarize_stage(approx, stage)
        hand_summary = summarize_stage(hand, stage)
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
        ],
        "area_crs": "EPSG:5179",
        "data_warning": [
            "Areas are method-comparison areas, not official inundation area.",
            "HAND uses relative water-level change and drainage-relative elevation, not absolute water-surface elevation.",
            "Do not use this comparison as exposure KPI evidence.",
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

"""Shrink the map layer payload the browser downloads.

The repositories keep full source attributes because the analysis services use them. The consoles only
read a handful of properties, so the HTTP payload keeps those and rounds coordinates to 5 decimals
(about 1 m). For Osong this cuts the gzip payload from about 4.0 MB to about 1 MB and drops the
building-register columns, which include lot addresses, from the public response.
"""

from typing import Any

COORDINATE_DECIMALS = 5

# Every property a console reads in a popup, legend, filter or style expression.
UI_PROPERTIES = frozenset({
    # Osong HAND and envelope cells
    "grid_id", "stage_index", "state", "label", "status", "hand_m", "hand_threshold_m",
    "observed_water_level_m", "distance_to_underpass_m",
    # WAMIS rivers
    "RIVNM_2", "CLAS2", "RIVCD_2",
    # buildings, roads, facilities, focus sites
    "official_feature_id", "name", "highway", "waterway", "amenity", "building", "facility_name", "kind", "note",
    # Seoul official flood traces and trace-overlay buildings
    "trace_id", "flood_depth_m", "damage_type", "district", "start_date", "end_date",
    "dong", "main_use", "above_ground_floors", "underground_floors", "max_trace_depth_m", "use_approval_date",
    # Seoul staged reveal of the official traces (depth order under the rainfall curve)
    "reveal_stage",
})


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, COORDINATE_DECIMALS)
    if isinstance(value, list):
        return [_round(item) for item in value]
    return value


def _slim_feature(feature: dict[str, Any]) -> dict[str, Any]:
    geometry = feature.get("geometry") or {}
    slim: dict[str, Any] = {
        "type": "Feature",
        "properties": {key: value for key, value in (feature.get("properties") or {}).items() if key in UI_PROPERTIES},
        "geometry": {**geometry, "coordinates": _round(geometry.get("coordinates"))} if geometry else geometry,
    }
    if "id" in feature:
        slim["id"] = feature["id"]
    return slim


def slim_layers(layers: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, layer in layers.items():
        data = layer.get("data") if isinstance(layer, dict) else None
        if isinstance(data, dict) and isinstance(data.get("features"), list):
            out[key] = {**layer, "data": {**data, "features": [_slim_feature(feature) for feature in data["features"]]}}
        else:
            out[key] = layer
    return out

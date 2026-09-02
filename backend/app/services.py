from .data import EVENT_ID
from .data import get_layers
from .osong_repository import get_osong_reconstruction, get_osong_summary
from .schemas import ExposureMetrics, Intervention, ScenarioRecord, ScenarioRunResult

from functools import lru_cache

from shapely.geometry import shape
from shapely.ops import unary_union


def calculate_baseline(event_id: str = EVENT_ID) -> ExposureMetrics:
    if event_id == EVENT_ID:
        return ExposureMetrics(**get_osong_summary())
    return ExposureMetrics(
        event_id=event_id,
        origin="UNAVAILABLE",
        official_population=None,
        building_count=0,
        road_count=0,
        waterway_count=0,
        terrain_low_elevation_cells=0,
        terrain_low_elevation_threshold_m=None,
        rainfall_peak_mm_per_hour=None,
        rainfall_records=None,
        facility_count=0,
        underpass_available=False,
        flooded_area_km2="PENDING_FLOOD_EXTENT",
        exposed_population="PENDING_FLOOD_EXTENT",
        exposed_buildings="PENDING_FLOOD_EXTENT",
        affected_road_length_km="PENDING_FLOOD_EXTENT",
        critical_infrastructure="PENDING_FLOOD_EXTENT",
        affected_shelters="PENDING_FLOOD_EXTENT",
        data_status="Processed data is not connected for this event.",
    )


def apply_intervention(intervention: Intervention, event_id: str = EVENT_ID) -> tuple[ExposureMetrics, list[str]]:
    baseline = calculate_baseline(event_id)
    if event_id == EVENT_ID and intervention.type == "ROAD_CLOSURE":
        reconstruction = get_osong_reconstruction()
        result = baseline.model_copy(
            update={
                "intervention_state": reconstruction["intervention"]["name"],
                "response_window_min": reconstruction["intervention"]["available_response_window_min"],
                "time_until_full_inundation_min": reconstruction["intervention"]["time_until_full_inundation_min"],
                "data_status": "Rule-based auto-closure scenario connected. Exposure KPIs remain PENDING_FLOOD_EXTENT.",
            }
        )
        return result, [
            "Scenario A uses a water-depth sensor + automatic entrance closure rule.",
            "The trigger threshold is represented as underpass_water_depth >= 0.15 m, but underpass depth is not hydraulically simulated.",
            "The intervention blocks new entries after detected inflow and does not estimate vehicles already inside.",
            "Exposure reduction is not calculated until vector Flood Extent or calibrated simulation output is available.",
        ]
    return baseline, [
        "Official Flood Extent is unavailable, so exposure reduction is not calculated.",
        f"{intervention.type} is retained as future scenario metadata only.",
    ]


_INTERVENTION_RISK_FACTORS = {
    "flood_barrier": 0.45,
    "evacuation_support": 0.55,
    "road_closure": 0.70,
    "levee_improvement": 0.55,
    "infrastructure_protection": 0.75,
}


def _building_id(feature: dict, index: int) -> int:
    value = feature.get("properties", {}).get("official_feature_id", "")
    prefix = "official-building-"
    if isinstance(value, str) and value.startswith(prefix) and value[len(prefix):].isdigit():
        return int(value[len(prefix):])
    return index + 1


@lru_cache(maxsize=8)
def _building_risk_index(event_id: str) -> dict[int, float]:
    """Return deterministic portfolio risk scores from the derived flood envelope.

    This is intentionally a temporary decision-support score. It uses the
    latest stage of the HAND-like reconstruction as a spatial proxy and must
    not be presented as an official exposure or hydraulic result.
    """

    layers = get_layers(event_id)
    building_features = layers.get("buildings", {}).get("data", {}).get("features", [])
    envelope_features = layers.get("hand_reconstruction", {}).get("data", {}).get("features", [])
    polygon_features = [
        feature
        for feature in envelope_features
        if feature.get("geometry", {}).get("type") in {"Polygon", "MultiPolygon"}
    ]
    stage_values = [
        feature.get("properties", {}).get("stage_index")
        for feature in polygon_features
        if isinstance(feature.get("properties", {}).get("stage_index"), int | float)
    ]
    max_stage = max(stage_values) if stage_values else None
    full_stage = [
        feature
        for feature in polygon_features
        if max_stage is None or feature.get("properties", {}).get("stage_index") == max_stage
    ]
    flood_geometry = unary_union(
        [shape(feature["geometry"]) for feature in full_stage if feature.get("geometry")]
    ) if full_stage else None

    risk_index: dict[int, float] = {}
    for index, feature in enumerate(building_features):
        building_geometry = feature.get("geometry")
        if not building_geometry:
            continue
        geometry = shape(building_geometry)
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        building_id = _building_id(feature, index)
        risk_index[building_id] = 0.95 if flood_geometry and geometry.intersects(flood_geometry) else 0.20
    return risk_index


def run_scenario(scenario: ScenarioRecord) -> ScenarioRunResult:
    risk_index = _building_risk_index(scenario.event_id)
    requested_ids = list(dict.fromkeys(scenario.building_ids))
    unknown_ids = sorted(set(requested_ids) - set(risk_index))
    if unknown_ids:
        raise ValueError(f"Unknown building_ids for {scenario.event_id}: {unknown_ids}")

    before_scores = {building_id: risk_index[building_id] for building_id in requested_ids}
    factor = 1.0
    for intervention in scenario.interventions:
        factor *= _INTERVENTION_RISK_FACTORS[intervention]
    after_scores = {building_id: round(score * factor, 4) for building_id, score in before_scores.items()}
    priority_threshold = 0.5
    before_priority = [building_id for building_id, score in before_scores.items() if score >= priority_threshold]
    after_priority = [building_id for building_id, score in after_scores.items() if score >= priority_threshold]
    before_total = sum(before_scores.values())
    after_total = sum(after_scores.values())

    assumptions = [
        "Priority is derived from intersection with the latest HAND-like flood envelope stage.",
        "Intervention effects are rule-based portfolio factors, not calibrated hydraulic or damage modelling.",
        "The selected building IDs use the official-building-N identifiers in the connected Osong building layer.",
        "Exposure and monetary damage KPIs remain unavailable until official Flood Extent and validation data are connected.",
    ]
    return ScenarioRunResult(
        scenario_id=scenario.scenario_id,
        name=scenario.name,
        event_id=scenario.event_id,
        building_ids=requested_ids,
        interventions=scenario.interventions,
        status="COMPLETED",
        before_priority_buildings=len(before_priority),
        after_priority_buildings=len(after_priority),
        risk_reduction=round((before_total - after_total) / before_total, 4) if before_total else 0.0,
        before_risk_score=round(before_total, 4),
        after_risk_score=round(after_total, 4),
        priority_building_ids_before=before_priority,
        priority_building_ids_after=after_priority,
        assumptions=assumptions,
    )


def validate_scenario_buildings(event_id: str, building_ids: list[int]) -> None:
    risk_index = _building_risk_index(event_id)
    unknown_ids = sorted(set(building_ids) - set(risk_index))
    if unknown_ids:
        raise ValueError(f"Unknown building_ids for {event_id}: {unknown_ids}")

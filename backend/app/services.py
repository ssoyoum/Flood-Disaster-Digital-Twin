from .data import EVENT_ID
from .osong_repository import get_osong_reconstruction, get_osong_summary
from .schemas import ExposureMetrics, Intervention


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

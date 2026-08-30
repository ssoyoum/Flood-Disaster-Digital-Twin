from .data import EVENT_ID
from .osong_repository import get_osong_summary
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
    return baseline, [
        "Official Flood Extent is unavailable, so exposure reduction is not calculated.",
        f"{intervention.type} is retained as future scenario metadata only.",
    ]

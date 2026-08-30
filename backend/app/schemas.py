from typing import Literal

from pydantic import BaseModel, Field


DataOrigin = Literal["VERIFIED", "DERIVED", "REANALYSIS", "TEMPORARY", "UNAVAILABLE"]
InterventionType = Literal[
    "EVACUATION",
    "ROAD_CLOSURE",
    "SHELTER_OPEN",
    "TEMPORARY_BARRIER",
    "LEVEE_IMPROVEMENT",
    "INFRASTRUCTURE_PROTECTION",
]


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[dict]


class FloodEvent(BaseModel):
    id: str
    name: str
    location: str
    data_year: int
    theme: str
    focus_feature: str
    analysis_flow: str
    source: str
    started_at: str
    ended_at: str
    origin: DataOrigin
    data_status: str
    flood_extent: FeatureCollection


class ExposureMetrics(BaseModel):
    event_id: str
    origin: DataOrigin = "DERIVED"
    official_population: int | None
    building_count: int
    road_count: int
    waterway_count: int
    terrain_low_elevation_cells: int
    terrain_low_elevation_threshold_m: float | None
    rainfall_peak_mm_per_hour: float | None
    rainfall_records: int | None
    facility_count: int
    underpass_available: bool
    flooded_area_km2: float | str
    exposed_population: int | str
    exposed_buildings: int | str
    affected_road_length_km: float | str
    critical_infrastructure: int | str
    affected_shelters: int | str
    data_status: str


class Intervention(BaseModel):
    type: InterventionType
    label: str
    description: str


class ScenarioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    intervention_type: InterventionType
    event_id: str = "osong-2023"


class ScenarioResult(BaseModel):
    scenario_id: str
    name: str
    intervention: Intervention
    baseline: ExposureMetrics
    result: ExposureMetrics
    reduction_percent: float
    assumptions: list[str]
    origin: Literal["TEMPORARY"] = "TEMPORARY"

from typing import Any, Annotated, Literal

from pydantic import BaseModel, Field


DataOrigin = Literal["VERIFIED", "DERIVED", "REANALYSIS", "TEMPORARY", "UNAVAILABLE"]
CoverageStatus = Literal["covered", "fallback", "unavailable"]
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
    model_type: str | None = None
    baseline_state: str | None = None
    intervention_state: str | None = None
    response_window_min: int | None = None
    time_until_full_inundation_min: int | None = None
    official_population: int | None
    building_count: int
    road_count: int
    waterway_count: int
    terrain_low_elevation_cells: int
    terrain_low_elevation_threshold_m: float | None
    rainfall_peak_mm_per_hour: float | None
    rainfall_peak_timestamp: str | None = None
    rainfall_peak_station_name: str | None = None
    rainfall_records: int | None
    water_level_peak_m: float | None = None
    water_level_peak_timestamp: str | None = None
    water_level_peak_station_name: str | None = None
    primary_water_level_peak_m: float | None = None
    primary_water_level_peak_timestamp: str | None = None
    facility_count: int
    underpass_available: bool
    safemap_floodmarks_available: bool | None = None
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


ScenarioIntervention = Literal[
    "flood_barrier",
    "evacuation_support",
    "road_closure",
    "levee_improvement",
    "infrastructure_protection",
]


class ScenarioCreateRequest(BaseModel):
    """Portfolio-facing scenario definition.

    ``intervention_type`` is kept as a compatibility field for the original
    single-intervention MVP endpoint. New clients should send ``interventions``.
    """

    name: str | None = Field(default=None, min_length=1, max_length=80)
    event_id: str = "osong-2023"
    building_ids: list[int] = Field(default_factory=list, max_length=500)
    interventions: list[ScenarioIntervention] = Field(default_factory=list, max_length=10)
    intervention_type: InterventionType | None = None


class ScenarioRecord(BaseModel):
    scenario_id: int
    name: str
    event_id: str
    building_ids: list[int]
    interventions: list[ScenarioIntervention]
    status: Literal["DRAFT", "COMPLETED"]
    created_at: str


class ScenarioRunResult(BaseModel):
    scenario_id: int
    name: str
    event_id: str
    building_ids: list[int]
    interventions: list[ScenarioIntervention]
    status: Literal["COMPLETED"]
    before_priority_buildings: int
    after_priority_buildings: int
    risk_reduction: float
    before_risk_score: float
    after_risk_score: float
    priority_building_ids_before: list[int]
    priority_building_ids_after: list[int]
    assumptions: list[str]
    origin: Literal["TEMPORARY"] = "TEMPORARY"


ClosureClassification = Literal[
    "PREEMPTIVE_BEFORE_LEVEE_FAILURE",
    "BEFORE_UNDERPASS_INFLOW",
    "AFTER_INFLOW_BEFORE_UNSAFE_DRIVING",
    "AFTER_UNSAFE_DRIVING",
    "AFTER_FULL_INUNDATION",
]


class ClosureTimingRequest(BaseModel):
    """What-if A: change the underpass entrance closure time.

    ``closure_times`` accepts ``HH:MM`` in the incident-day local time or a full
    ISO-8601 timestamp. The analysis only rearranges observed incident
    timestamps; it does not model hydraulics, traffic, or casualties.
    """

    closure_times: list[str] = Field(default_factory=lambda: ["08:25", "08:30", "08:35"], min_length=1, max_length=10)


class ClosureTimingMilestone(BaseModel):
    state: str
    label: str
    time: str


class ClosureTimingScenario(BaseModel):
    closure_time: str
    state_at_closure: str | None
    label_at_closure: str | None
    classification: ClosureClassification
    entry_blocked_before_inflow: bool
    minutes_before_underpass_inflow: int
    minutes_before_unsafe_driving: int
    minutes_before_full_inundation: int
    lead_time_vs_detection_trigger_min: int


class ClosureTimingResult(BaseModel):
    event_id: str
    analysis: Literal["closure_timing_whatif"] = "closure_timing_whatif"
    origin: Literal["TEMPORARY"] = "TEMPORARY"
    coverage_status: CoverageStatus
    coverage_note: str
    detection_trigger_time: str
    detection_trigger_basis: str
    milestones: list[ClosureTimingMilestone]
    scenarios: list[ClosureTimingScenario]
    assumptions: list[str]
    limitations: list[str]


class InflowDelayRequest(BaseModel):
    """What-if B: delay underpass inflow by a user-supplied time assumption.

    The delay is a scenario parameter, not an estimate of barrier hydraulics or
    discharge reduction. Downstream reconstruction milestones are shifted by
    the requested number of minutes.
    """

    delay_minutes: list[Annotated[int, Field(ge=0, le=180)]] = Field(
        default_factory=lambda: [5, 10, 15],
        min_length=1,
        max_length=10,
    )


class InflowDelayMilestone(BaseModel):
    state: str
    label: str
    baseline_time: str
    shifted_time: str
    shifted_by_min: int


class InflowDelayScenario(BaseModel):
    delay_minutes: int
    assumption: str
    milestones: list[InflowDelayMilestone]
    minutes_gained_before_unsafe_driving: int
    minutes_gained_before_full_inundation: int


class InflowDelayResult(BaseModel):
    event_id: str
    analysis: Literal["inflow_delay_whatif"] = "inflow_delay_whatif"
    origin: Literal["TEMPORARY"] = "TEMPORARY"
    coverage_status: CoverageStatus
    coverage_note: str
    shifted_states: list[str]
    scenarios: list[InflowDelayScenario]
    assumptions: list[str]
    limitations: list[str]


class AgentToolDescriptor(BaseModel):
    name: str
    description: str
    input_fields: list[str]
    output: str


class AgentToolCallRequest(BaseModel):
    """Common request envelope for registered Agent tools."""

    event_id: str = "osong-2023"
    closure_times: list[str] | None = None
    delay_minutes: list[Annotated[int, Field(ge=0, le=180)]] | None = None
    radii_m: list[Annotated[int, Field(ge=50, le=20000)]] | None = None


class AgentToolCallResult(BaseModel):
    tool_name: str
    event_id: str
    result: dict


AgentWorkflowName = Literal[
    "situation",
    "closure_timing",
    "inflow_delay",
    "exposure_inventory",
]


class AgentWorkflowRequest(BaseModel):
    """Explicit workflow request for orchestration before natural-language planning."""

    workflow: AgentWorkflowName
    event_id: str = "osong-2023"
    closure_times: list[str] | None = None
    delay_minutes: list[Annotated[int, Field(ge=0, le=180)]] | None = None
    radii_m: list[Annotated[int, Field(ge=50, le=20000)]] | None = None


class AgentToolTrace(BaseModel):
    order: int
    tool_name: str
    status: Literal["completed"]
    result_keys: list[str]


class AgentWorkflowResult(BaseModel):
    workflow: AgentWorkflowName
    event_id: str
    status: Literal["COMPLETED"]
    tool_calls: list[AgentToolTrace]
    result: dict
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    coverage_status: str | None = None
    coverage_note: str | None = None


AgentPlanStatus = Literal["READY", "NEEDS_CLARIFICATION", "UNSUPPORTED"]
AgentPlannerChoice = Literal["auto", "deterministic", "llm"]


class AgentIntentPlanRequest(BaseModel):
    """Natural-language request to deterministic workflow planning."""

    message: str = Field(min_length=1, max_length=1000)
    event_id: str = "osong-2023"
    planner: AgentPlannerChoice = "auto"


class AgentIntentPlanResult(BaseModel):
    """Inspectable plan; planning never executes a tool or invents results."""

    status: AgentPlanStatus
    event_id: str
    planner_used: Literal["deterministic", "llm"] = "deterministic"
    planner_note: str = ""
    workflow: AgentWorkflowName | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    tool_names: list[str] = Field(default_factory=list)
    reason: str
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ExposureRing(BaseModel):
    radius_m: int
    area_km2: float
    buildings: int
    roads_km: float
    facilities: int


class InventorySource(BaseModel):
    key: str
    label: str
    source: str
    snapshot: str | None
    status: str
    feature_count: int


class ExposureInventoryResult(BaseModel):
    """Counts of connected inventory layers around the event focus feature.

    This is deliberately independent of any flood envelope. It answers "what is
    inside this radius", never "what was flooded".
    """

    event_id: str
    analysis: Literal["exposure_inventory"] = "exposure_inventory"
    origin: Literal["DERIVED"] = "DERIVED"
    coverage_status: CoverageStatus
    coverage_note: str
    focus_feature: str
    focus_feature_layer: str
    focus_feature_source: str
    inventory_sources: list[InventorySource]
    rings: list[ExposureRing]
    assumptions: list[str]
    limitations: list[str]

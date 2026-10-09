from datetime import datetime
from typing import Any, Annotated, Literal

from pydantic import BaseModel, Field, field_validator


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
    reduction_percent: float | None
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
    status: Literal["DRAFT", "COMPLETED", "UNAVAILABLE"]
    created_at: str


class ScenarioRunResult(BaseModel):
    scenario_id: int
    name: str
    event_id: str
    building_ids: list[int]
    interventions: list[ScenarioIntervention]
    status: Literal["COMPLETED", "UNAVAILABLE"]
    before_priority_buildings: int | None
    after_priority_buildings: int | None
    risk_reduction: float | None
    before_risk_score: float | None
    after_risk_score: float | None
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


class FacilityAgentScope(BaseModel):
    facility_id: str | None = Field(default=None, min_length=1, max_length=100)
    observation_at: str | None = None

    @field_validator("observation_at")
    @classmethod
    def _valid_observation_time(cls, value: str | None) -> str | None:
        if value is not None:
            if "T" not in value:
                raise ValueError("observation_at must be an ISO date-time; select a replay time in the facility view.")
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


class AgentToolCallRequest(FacilityAgentScope):
    """Common request envelope for registered Agent tools."""

    event_id: str = "osong-2023"
    closure_times: list[str] | None = None
    delay_minutes: list[Annotated[int, Field(ge=0, le=180)]] | None = None
    radii_m: list[Annotated[int, Field(ge=50, le=20000)]] | None = None
    reduction_m: Annotated[float, Field(ge=0, le=2.5)] | None = None
    comparison_type: Literal["closure_timing", "inflow_delay"] = "closure_timing"
    # Seoul 2022 tools
    thresholds_mm_per_hour: list[Annotated[float, Field(gt=0, le=200)]] | None = None
    alert_times: list[str] | None = None
    storage_m3: Annotated[float, Field(gt=0, le=5_000_000)] | None = None
    capacity_mm_per_hour: Annotated[float, Field(gt=0, le=200)] | None = None
    runoff_coefficient: Annotated[float, Field(gt=0, le=1.0)] | None = None
    # Pohang 2022 / Andong-Uiseong 2026 tool
    intervention_id: str | None = None
    action_times: list[str] | None = None


class AgentToolCallResult(BaseModel):
    tool_name: str
    event_id: str
    result: dict


class HandThresholdRequest(BaseModel):
    reduction_m: Annotated[float, Field(ge=0, le=2.5)] = 1.5


class HandThresholdStage(BaseModel):
    stage_index: int
    state: str
    time: str
    baseline_threshold_m: float
    scenario_threshold_m: float
    baseline_cell_count: int
    scenario_cell_count: int
    removed_cell_count: int
    selected_grid_ids: list[str]
    removed_grid_ids: list[str]


class HandThresholdResult(BaseModel):
    event_id: str
    analysis: Literal["hand_threshold_sensitivity"]
    reduction_m: float
    coverage_status: str
    coverage_note: str
    stages: list[HandThresholdStage]
    assumptions: list[str]
    limitations: list[str]


class AgentExampleQuestion(BaseModel):
    """An answerable starter question, offered as a chip before anything is typed."""

    workflow: str
    label: str
    question: str


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
    suggestions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AgentConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1500)


class AgentAskRequest(FacilityAgentScope):
    message: str = Field(min_length=1, max_length=1000)
    event_id: str = "osong-2023"
    history: list[AgentConversationTurn] = Field(default_factory=list, max_length=6)


class AgentAskToolTrace(BaseModel):
    order: int
    tool_name: str
    reason: str
    parameters: dict[str, Any]
    result: dict[str, Any]


class AgentAskFailure(BaseModel):
    stage: Literal["model", "validation", "tool", "answer"]
    code: str
    step: int = Field(ge=0)
    tool_name: str | None = None


class AgentAskDiagnostics(BaseModel):
    request_id: str
    duration_ms: int = Field(ge=0)
    model_steps: int = Field(ge=0)
    model_requests: int = Field(ge=0)
    completion_source: Literal["model", "registered_tools", "capability", "clarification", "unavailable"]
    context_mode: Literal["current", "reused", "updated", "ambiguous"] = "current"
    failures: list[AgentAskFailure] = Field(default_factory=list)


class AgentAskResult(BaseModel):
    facility_id: str | None = None
    event_id: str
    status: Literal["ANSWERED", "NEEDS_DATA", "UNAVAILABLE"]
    answer: str
    tool_calls: list[AgentAskToolTrace] = Field(default_factory=list)
    evidence_calls: list[int] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    model: str | None = None
    diagnostics: AgentAskDiagnostics | None = None
    context_note: str = ""


class ScenarioComparisonResult(BaseModel):
    """Baseline comparison limited to supported, domain-derived time measures."""

    event_id: str
    analysis: Literal["scenario_comparison"] = "scenario_comparison"
    comparison_type: Literal["closure_timing", "inflow_delay"]
    coverage_status: CoverageStatus
    coverage_note: str
    baseline: dict[str, Any]
    comparisons: list[dict[str, Any]]
    provenance: list[dict[str, Any]]
    assumptions: list[str]
    limitations: list[str]


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


class AlertTimingRequest(BaseModel):
    """Seoul what-if: send the low-lying flood alert when a rain gauge crosses a threshold or at a fixed time."""

    station: str = "신림P"
    thresholds_mm_per_hour: list[float] = Field(default_factory=lambda: [30.0, 50.0, 95.0], max_length=10)
    alert_times: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("thresholds_mm_per_hour")
    @classmethod
    def _thresholds_in_range(cls, values: list[float]) -> list[float]:
        if any(value <= 0 or value > 200 for value in values):
            raise ValueError("thresholds_mm_per_hour must be within (0, 200]")
        return values


class StorageCaptureRequest(BaseModel):
    """Seoul what-if: how much rain above the drainage capacity an assumed storage tunnel could hold."""

    station: str = "신림P"
    storage_m3: float = Field(default=400_000, gt=0, le=5_000_000)
    capacity_mm_per_hour: float = Field(default=95.0, gt=0, le=200)
    catchment_area_km2: float | None = Field(default=None, gt=0, le=200)
    runoff_coefficient: float = Field(default=1.0, gt=0, le=1.0)


class ResponseTimingRequest(BaseModel):
    """Timeline cases: move one response action (parking entry ban, evacuation order, alert) to other times."""

    intervention_id: str
    action_times: list[str] = Field(default_factory=list, max_length=10)


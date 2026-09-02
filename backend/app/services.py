from .data import EVENT_ID
from .data import get_layers
from .osong_repository import get_osong_reconstruction, get_osong_summary
from .schemas import ExposureMetrics, Intervention, ScenarioRecord, ScenarioRunResult

from datetime import datetime, timedelta
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


class ReconstructionUnavailable(LookupError):
    """Raised when an event has no connected incident reconstruction timeline."""


_CLOSURE_MILESTONES = ("levee_failure", "underpass_inflow", "unsafe_driving", "full_inundation")


def _reconstruction_for(event_id: str) -> dict:
    if event_id == EVENT_ID:
        return get_osong_reconstruction()
    raise ReconstructionUnavailable(
        f"Incident reconstruction timeline is not connected for {event_id}"
    )


def _parse_closure_time(value: str, reference: datetime) -> datetime:
    """Accept ``HH:MM`` on the incident day, or a full ISO-8601 timestamp."""

    text = value.strip()
    try:
        if len(text) <= 5 and ":" in text:
            hour, minute = (int(part) for part in text.split(":"))
            return reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"closure_time '{value}' must be HH:MM on the incident day or an ISO-8601 timestamp"
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=reference.tzinfo)


def _classify_closure(closure: datetime, milestone: dict[str, datetime]) -> str:
    if closure <= milestone["levee_failure"]:
        return "PREEMPTIVE_BEFORE_LEVEE_FAILURE"
    if closure <= milestone["underpass_inflow"]:
        return "BEFORE_UNDERPASS_INFLOW"
    if closure < milestone["unsafe_driving"]:
        return "AFTER_INFLOW_BEFORE_UNSAFE_DRIVING"
    if closure < milestone["full_inundation"]:
        return "AFTER_UNSAFE_DRIVING"
    return "AFTER_FULL_INUNDATION"


def analyze_closure_timing(event_id: str, closure_times: list[str]) -> dict:
    """What-if A: rearrange the underpass closure time against observed milestones.

    Every returned number is a difference between incident timestamps that are
    already stored in the reconstruction timeline. No hydraulic, traffic, or
    casualty estimate is produced here.
    """

    reconstruction = _reconstruction_for(event_id)
    replay = reconstruction["replay"]
    times = {entry["state"]: datetime.fromisoformat(entry["time"]) for entry in replay}
    missing = [state for state in _CLOSURE_MILESTONES if state not in times]
    if missing:
        raise ReconstructionUnavailable(
            f"Reconstruction timeline for {event_id} is missing required states: {missing}"
        )

    milestone = {state: times[state] for state in _CLOSURE_MILESTONES}
    trigger_time = datetime.fromisoformat(reconstruction["intervention"]["trigger_time"])
    ordered_replay = sorted(replay, key=lambda entry: entry["time"])

    scenarios = []
    for value in dict.fromkeys(closure_times):
        closure = _parse_closure_time(value, milestone["underpass_inflow"])
        state_at_closure = None
        for entry in ordered_replay:
            if datetime.fromisoformat(entry["time"]) <= closure:
                state_at_closure = entry
            else:
                break
        scenarios.append(
            {
                "closure_time": closure.isoformat(),
                "state_at_closure": state_at_closure["state"] if state_at_closure else None,
                "label_at_closure": state_at_closure["label"] if state_at_closure else None,
                "classification": _classify_closure(closure, milestone),
                "entry_blocked_before_inflow": closure <= milestone["underpass_inflow"],
                "minutes_before_underpass_inflow": _minutes(closure, milestone["underpass_inflow"]),
                "minutes_before_unsafe_driving": _minutes(closure, milestone["unsafe_driving"]),
                "minutes_before_full_inundation": _minutes(closure, milestone["full_inundation"]),
                "lead_time_vs_detection_trigger_min": _minutes(closure, trigger_time),
            }
        )
    scenarios.sort(key=lambda item: item["closure_time"])

    return {
        "event_id": event_id,
        "coverage_status": "fallback",
        "coverage_note": (
            "Incident timestamps are reconstruction values whose confidence is NEEDS_SOURCE_PAGE. "
            "Timing differences are exact, but the underlying milestone times still need source-page evidence."
        ),
        "detection_trigger_time": trigger_time.isoformat(),
        "detection_trigger_basis": reconstruction["intervention"]["trigger_basis"],
        "milestones": [
            {"state": entry["state"], "label": entry["label"], "time": entry["time"]}
            for entry in ordered_replay
        ],
        "scenarios": scenarios,
        "assumptions": [
            "Closure blocks new vehicle entry from the given time onward.",
            "Observed milestone times are held fixed; only the closure time changes.",
            "A positive minutes_before_* value means the closure happens before that milestone.",
            "lead_time_vs_detection_trigger_min compares against Scenario A, which closes at detected inflow.",
        ],
        "limitations": [
            "This is timeline arithmetic on reconstructed incident timestamps, not a hydraulic or traffic simulation.",
            "Vehicles already inside the underpass at closure time are not estimated.",
            "No casualty, damage-cost, or exposure reduction is derived from these time windows.",
            "Underpass water depth is not computed; the 0.15 m detection threshold stays a rule-based trigger.",
        ],
    }


def analyze_inflow_delay(event_id: str, delay_minutes: list[int]) -> dict:
    """What-if B: shift underpass inflow and downstream milestones by ``Δt``.

    This is an explicit timing assumption for a hypothetical inflow-reduction
    measure. It does not calculate discharge, water depth, velocity, traffic,
    or damage. The baseline timestamps remain the stored reconstruction values.
    """

    reconstruction = _reconstruction_for(event_id)
    replay = reconstruction["replay"]
    times = {entry["state"]: datetime.fromisoformat(entry["time"]) for entry in replay}
    shifted_states = ("underpass_inflow", "unsafe_driving", "full_inundation")
    missing = [state for state in shifted_states if state not in times]
    if missing:
        raise ReconstructionUnavailable(
            f"Reconstruction timeline for {event_id} is missing required states: {missing}"
        )

    ordered_replay = sorted(replay, key=lambda entry: entry["time"])
    baseline_times = {state: times[state] for state in shifted_states}
    scenarios = []
    for value in dict.fromkeys(delay_minutes):
        if value < 0 or value > 180:
            raise ValueError("delay_minutes values must be between 0 and 180")
        shift = timedelta(minutes=value)
        milestones = []
        for entry in ordered_replay:
            state = entry["state"]
            if state not in shifted_states:
                continue
            baseline_time = baseline_times[state]
            milestones.append(
                {
                    "state": state,
                    "label": entry["label"],
                    "baseline_time": baseline_time.isoformat(),
                    "shifted_time": (baseline_time + shift).isoformat(),
                    "shifted_by_min": value,
                }
            )
        scenarios.append(
            {
                "delay_minutes": value,
                "assumption": f"Hypothetical measure delays underpass inflow by {value} minutes.",
                "milestones": milestones,
                "minutes_gained_before_unsafe_driving": value,
                "minutes_gained_before_full_inundation": value,
            }
        )

    return {
        "event_id": event_id,
        "coverage_status": "fallback",
        "coverage_note": (
            "The delay is a user-supplied timing assumption. Baseline timestamps are reconstruction values "
            "whose confidence is NEEDS_SOURCE_PAGE; shifted times are scenario arithmetic only."
        ),
        "shifted_states": list(shifted_states),
        "scenarios": scenarios,
        "assumptions": [
            "The hypothetical measure delays underpass inflow by the requested Δt minutes.",
            "Underpass inflow, unsafe driving, and full inundation milestones shift together; earlier milestones stay fixed.",
            "The baseline timeline is held fixed and is not recalibrated by the intervention assumption.",
        ],
        "limitations": [
            "This is a timeline-shift assumption, not a barrier hydraulics or inflow-volume calculation.",
            "No discharge, flow cross-section, roughness, water depth, velocity, traffic, casualty, or damage estimate is produced.",
            "The shifted milestones do not establish that the physical event would follow the same progression.",
            "Underlying incident timestamps still need source-page evidence.",
        ],
    }


def _minutes(start: datetime, end: datetime) -> int:
    return round((end - start).total_seconds() / 60)

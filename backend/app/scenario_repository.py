"""In-memory storage for the portfolio-facing scenario workflow.

The project currently runs without PostGIS. This repository keeps the API
contract stable while making it straightforward to replace the store with a
database-backed implementation later.
"""

from copy import deepcopy
from datetime import datetime, timezone

from .schemas import ScenarioIntervention, ScenarioRecord


_SCENARIOS: dict[int, ScenarioRecord] = {}
_NEXT_SCENARIO_ID = 1


def create_scenario(
    *,
    name: str | None,
    event_id: str,
    building_ids: list[int],
    interventions: list[ScenarioIntervention],
) -> ScenarioRecord:
    global _NEXT_SCENARIO_ID

    scenario_id = _NEXT_SCENARIO_ID
    _NEXT_SCENARIO_ID += 1
    scenario = ScenarioRecord(
        scenario_id=scenario_id,
        name=name or f"Scenario {scenario_id}",
        event_id=event_id,
        building_ids=list(building_ids),
        interventions=list(interventions),
        status="DRAFT",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _SCENARIOS[scenario_id] = scenario
    return deepcopy(scenario)


def get_scenario(scenario_id: int) -> ScenarioRecord | None:
    scenario = _SCENARIOS.get(scenario_id)
    return deepcopy(scenario) if scenario else None


def mark_completed(scenario_id: int) -> ScenarioRecord:
    scenario = _SCENARIOS[scenario_id]
    scenario.status = "COMPLETED"
    return deepcopy(scenario)

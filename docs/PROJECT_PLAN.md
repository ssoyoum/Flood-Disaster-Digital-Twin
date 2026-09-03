# FloodOps Project Plan

Last updated: 2026-09-04

## Definition

FloodOps is a Counterfactual Disaster Digital Twin.

It reconstructs a real historical disaster with observed and spatial data, then changes intervention conditions under the same event to compare response options.

FloodOps is not:

- an AI flood prediction model
- a precise future forecasting system
- an official flood map replacement
- a validated hydraulic simulation system
- a simple news timeline

Core value:

> Historical Disaster Reconstruction + Counterfactual Intervention + Decision Support

## Reference Case

The first reference case is:

> 2023 Osong Underpass Flood - Miho River and Gungpyeong 2 Underpass

Main analysis flow:

```text
rainfall
-> Miho River water-level rise
-> overflow
-> temporary levee breach
-> underpass inflow
-> underpass risk-state change
-> response intervention timing
```

The key question is not only where water was present. The key question is when the event state became dangerous and whether a different intervention timing could have changed the response window.

## Phase 1: FloodOps 1.0

Phase 1 is an Observed Event Twin / Historical Reconstruction MVP.

Included:

- KMA observed rainfall
- HRFCO/Flood Control Office observed water level
- official incident timeline
- WAMIS river geometry
- SGIS administrative boundary
- Copernicus DEM
- official GIS Building Integrated Information
- OSM historical snapshot for QA and context
- Gungpyeong 2 underpass thematic layer
- Historical Replay
- baseline scenario
- one or more rule-based interventions
- deterministic Agent workflows for situation, closure timing, inflow delay, and exposure inventory
- optional LLM intent planner with deterministic fallback
- portfolio response scenario API for building-level intervention comparison
- provenance and limitations
- temporary approximate flood envelope for visual reconstruction

Not included as validated claims:

- official flood extent
- measured depth
- measured velocity
- final exposure KPIs without valid flood geometry
- fatality, damage-cost, or official loss-reduction estimates

## Current Implementation Snapshot

As of 2026-09-04, the Osong MVP is presentation-ready at the backend and light
frontend baseline. Historical Replay, HAND-like reconstruction, What-if A/B,
Agent workflow orchestration, the optional LLM planner, and the portfolio
scenario API are connected and covered by automated tests.

The `ui/dark-console` branch contains an in-progress dark console presentation
layer. It reuses the existing APIs and data, but still requires browser smoke
testing, MapLibre warning cleanup, provenance/limitation review, and a focused
commit before it is treated as complete.

Current validation command results:

- backend: `58 passed`
- frontend: `npm run build` passed; Vite reported only the existing large-chunk warning

## Current Spatial Reconstruction

The current `approx_flood_envelope` is a DEM low-elevation based time-varying approximate envelope.

It combines:

- observed rainfall
- observed water level
- DEM low-elevation context
- WAMIS river geometry
- Gungpyeong 2 underpass location
- incident timeline stages

Classification:

- `TEMPORARY`
- `DERIVED`
- `APPROXIMATION`

Purpose:

- make Historical Replay spatially visible
- show a plausible event-state envelope by timeline stage
- support MVP interaction and communication

Limit:

- not official Flood Extent
- not 2D hydraulic simulation
- not depth or velocity
- not final exposure geometry

## Phase 1 What-if Scope

MVP What-if scenarios should stay small and defensible.

Preferred first scenarios:

- vehicle entry closure at alternative times
- temporary flood barrier presence or absence
- levee height or levee condition variation, only if assumptions are explicit

Allowed outputs:

- response window
- closure state
- risk-state transition
- access allowed / blocked
- approximate envelope difference if available
- baseline versus scenario visual comparison

Do not estimate deaths prevented, property damage avoided, or official damage reduction without a validated model and evidence.

## Phase 2: Physics-Enhanced Twin

Phase 2 adds calibrated physical simulation to the reconstruction twin.

Possible engines:

- HEC-RAS 2D
- LISFLOOD-FP

Phase 2 target:

```text
breach location / geometry
-> flow boundary conditions
-> calibrated 2D hydraulics
-> time-varying depth / velocity
-> validation against observed flood evidence
-> GIS layer
-> API
-> React UI
```

HEC-RAS is a simulation engine, not the project identity.

## Phase 3: Operational Twin

Phase 3 may connect:

- real-time sensors
- weather forecasts
- live river levels
- facility status
- risk prediction
- warning automation
- operational response comparison

This is outside the current MVP.

## Future Case Expansion

Candidate cases remain:

- 2022 Seoul Urban Flood
- 2022 Pohang Typhoon Flood
- 2023 Osong Underpass Flood
- 2024 Iksan Extreme Rainfall Flood
- 2026 Andong-Uiseong Compound Flood

Each case must separate:

- event year
- data vintage
- boundary snapshot
- acquisition date
- observed data
- derived reconstruction output
- validation material

## Success Criteria

For the Osong MVP:

- the historical sequence is replayable
- map state changes with time
- observed rainfall and water level are visible
- Gungpyeong 2 underpass is clearly identified
- at least one intervention can be compared with baseline
- provenance and uncertainty are visible
- approximate flood envelope is clearly labeled as temporary derived approximation
- exposure KPIs that need official flood geometry remain pending
- backend tests and frontend build pass

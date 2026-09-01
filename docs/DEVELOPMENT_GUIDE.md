# FloodOps Development Guide

Last updated: 2026-09-01

## Project Identity

FloodOps is not a future flood prediction system.

FloodOps is a disaster decision-support Digital Twin PoC that reconstructs real historical disaster events with observed and spatial data, then compares counterfactual interventions under the same event conditions.

Core question:

> What happened during the Osong flood, and how might the situation have changed if a different intervention had been applied?

The product value is:

> Historical Disaster Reconstruction + Counterfactual Intervention + Decision Support

Do not describe FloodOps as an AI flood predictor, a precise future forecasting model, an official flood map replacement, or a validated hydraulic simulation system.

## Phase Definitions

### Phase 1: Historical Reconstruction MVP

Phase 1 reconstructs the 2023 Osong event from available observed and official records.

Primary inputs:

- KMA observed rainfall time series
- HRFCO/Flood Control Office observed water-level time series
- WAMIS river geometry
- DEM
- levee and incident-related spatial context
- Gungpyeong 2 underpass geometry
- official incident timeline
- official flood marks or other validation material when available

Target flow:

```text
rainfall
-> river water level
-> river state
-> levee event
-> low-lying / flood-prone spatial state
-> Gungpyeong 2 underpass
```

This is not a news timeline. The map state must change with time so the event behaves like a Historical Twin.

### Phase 2: Physics-Enhanced Twin

Phase 2 adds calibrated physical simulation after the reconstruction MVP is working.

Possible engines:

- HEC-RAS 2D
- LISFLOOD-FP

Required inputs before treating results as physical flood simulation:

- levee breach location, section, width, and timing
- discharge or boundary conditions
- water level / discharge relationship
- drainage and underpass structure
- Manning's n or equivalent roughness parameters
- time-varying depth and velocity validation data
- official flood extent or observed inundation evidence

HEC-RAS is a simulation engine. It is not the Digital Twin itself.

### Phase 3: Operational Twin

Phase 3 may connect real-time sensors, forecasts, facility status, warning automation, and operational decision support.

Do not build Phase 3 behavior into the MVP unless explicitly requested.

## Approximate Flood Envelope

The current `approx_flood_envelope` layer is:

- `TEMPORARY`
- `DERIVED`
- `APPROXIMATION`

It is a DEM low-elevation based, time-varying approximate flood envelope used for MVP visualization and historical reconstruction testing.

It must not be represented as:

- actual observed flood extent
- official Flood Extent
- measured flood depth
- measured flow velocity
- precise flood prediction
- final exposure-analysis geometry

Valid use:

- show a plausible time-changing spatial state during Historical Replay
- connect rainfall, water level, DEM, river geometry, and incident events in the UI
- explain where the model has enough context and where it remains uncertain

Invalid use:

- compute final flooded buildings
- compute final exposed population
- claim official inundation area
- claim avoided fatalities, avoided damage cost, or verified damage reduction

## HAND Improvement Direction

The next reconstruction improvement should move from simple low-elevation thresholds toward:

> HAND (Height Above Nearest Drainage) + observed water level + DEM connectivity

Conceptual workflow:

```text
DEM
-> drainage / river network
-> relative height above nearest drainage
-> observed time-varying water level
-> potential flood-connected area
```

HAND output is still derived reconstruction output. It is not official Flood Extent.

## What-if Engine

Counterfactual scenarios are applied only after the historical baseline is defined.

The scenario must keep the same event conditions and change only the intervention assumptions.

MVP scenarios are limited to a small set:

- vehicle entry closure
- temporary flood barrier
- levee height or levee condition change

Recommended first options:

- vehicle closure at 08:25 / 08:30 / 08:35
- barrier installed or not installed
- levee +0.5m / +1.0m if the model can support it

Do not exaggerate scenario outputs when physical mechanisms are not modeled.

## What-if Output Rules

Allowed outputs:

- time-varying potential flood envelope
- changing risk state
- closure active / inactive state
- response start time
- accessible or blocked underpass state
- relationship between hazard state and critical facilities
- baseline versus scenario map difference when calculable

Forbidden without validation:

- fatality reduction
- property-damage reduction
- official loss avoidance
- precise avoided-exposure percentages
- depth or velocity claims

If official Flood Extent is missing, exposure KPIs remain `PENDING_FLOOD_EXTENT`.

## Backend Rules

- Keep route logic thin.
- Put file loading and data status logic in repository/service layers.
- Do not read large raw data on every request.
- Prefer processed snapshots for API responses.
- Missing layers must return an unavailable layer status instead of failing the whole event.
- Preserve distinction between observed, reanalysis, derived, temporary, and unavailable data.

## Frontend Rules

- The default screen should show the usable reconstruction experience, not a landing page.
- Historical Replay must update both timeline state and map state.
- Baseline / Intervention comparison must make its assumptions visible.
- Data provenance must show source, vintage, role, and limitations.
- Developer-only status values should not dominate the user-facing UI.
- Basemap is geographic context only and may reflect a different date from historical analysis layers.

## Data Rules

- Never modify raw files.
- Save raw snapshots under `data/raw/`.
- Save processed outputs under `data/processed/`.
- Keep provenance and availability in `data/manifests/`.
- Separate `event_year`, `data_vintage`, `boundary_snapshot`, and acquisition date.
- Do not infer missing years from filenames unless the dataset metadata supports it.
- Mark unknown data vintage as `UNKNOWN` or `NOT RECORDED`.

Data classification:

- `OBSERVATION`: measured official or instrument data, such as KMA AWS or HRFCO water level.
- `REANALYSIS`: external reanalysis data, such as NASA POWER raw data.
- `DERIVED`: project-generated transformation or analysis output.
- `TEMPORARY`: provisional MVP layer or assumption.
- `UNAVAILABLE`: expected data not currently available.

## Documentation Sync

After meaningful implementation, data processing, analysis, verification, or bug fixing:

- update `TODO.md` only after the actual state changes
- update `WORKLOG.md` with the completed work and verification result
- update `docs/data-quality.md` only when a data-quality issue is found or resolved
- update `docs/performance.md` only when a performance issue or optimization is found

Before any requested commit, check that `TODO.md` and `WORKLOG.md` do not contradict the actual code and data state.

## Testing

Use focused verification for the changed surface:

- backend repository/API changes: `python -m pytest backend/tests`
- frontend behavior/type changes: `npm run build`
- spatial processing scripts: validate feature count, CRS, geometry type, and output paths

Do not use successful builds as proof that a derived layer is scientifically valid. Scientific validity comes from provenance, method, assumptions, and comparison with validation data.

## Avoid

Do not:

- present FloodOps as an AI prediction model
- present approximate envelopes as official flood extents
- present basemap content as historical 2023 data
- silently mix observed data and derived outputs
- calculate final exposure KPIs without valid flood geometry
- add Phase 2 or Phase 3 architecture before the MVP needs it
- replace official incident data with OSM, NASA, or generic global data when official event data exists

## Final Definition

FloodOps reconstructs real historical disasters with spatial and temporal data, then compares counterfactual disaster-response interventions under the same event conditions.

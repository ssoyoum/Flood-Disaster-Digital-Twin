# FloodOps Decisions

Last updated: 2026-09-01

This document records important design and data decisions. Detailed daily work belongs in `WORKLOG.md`; current priorities belong in `TODO.md`.

## D-001 Target Reference Case

- Date: 2026-08-30
- Decision: Start the MVP with `osong-2023`.
- Reason: The Osong case connects river flooding, levee failure, transport infrastructure, underpass inundation, and response timing in one compact reference case.
- Impact: Data acquisition, API design, UI, and scenario logic prioritize the 2023 Osong event before expanding to other cases.

## D-002 Keep Event Year and Data Vintage Separate

- Date: 2026-08-30
- Decision: Track `event_year`, `data_vintage`, `boundary_snapshot`, `snapshot_date`, and acquisition date separately.
- Reason: Historical reconstruction can use data collected or published at different times.
- Impact: The UI and manifests must not imply that every layer is 2023 data just because the event year is 2023.

## D-003 Separate Official Event Evidence from Spatial Context Data

- Date: 2026-08-30
- Decision: Use official or observed data for rainfall, water level, incident evidence, flood marks, damage, and relief records when available. Use OSM, WorldPop, Copernicus DEM, and similar data as spatial context or fallback analysis inputs.
- Reason: Event causality and impact interpretation should not be replaced by generic global/open data when official event evidence exists.
- Impact: OSM/NASA-style sources are not presented as official incident evidence.

## D-004 Population Data Priority

- Date: 2026-08-30
- Decision: Prioritize official fine-grained population data, then official eup/myeon/dong population plus WorldPop spatial distribution, then WorldPop-only fallback.
- Reason: Total population and regional comparison values should come from official statistics.
- Impact: WorldPop is used for spatial distribution estimation, not as a direct replacement for official local totals.

## D-005 NASA POWER Classification

- Date: 2026-08-30
- Decision: NASA POWER raw data is classified as `REANALYSIS`; project-converted CSV outputs are classified as `DERIVED`.
- Reason: The project did not create the NASA reanalysis source, but it did create processed derivatives.
- Impact: KMA AWS/ASOS remains the primary observed rainfall source for the Osong reconstruction.

## D-006 Use API Downloads as Historical Snapshots

- Date: 2026-08-30
- Decision: Approved external API responses are stored as raw historical snapshots. The running application should not call external historical-data APIs on every request.
- Reason: The project reconstructs past events and needs reproducible data states.
- Impact: APIs are useful for periodic dataset refresh, not live runtime dependency in the MVP.

## D-007 Gungpyeong 2 Underpass MVP Scope

- Date: 2026-08-30
- Decision: Model Gungpyeong 2 underpass as the single core transport facility for the Osong MVP.
- Reason: It is the central thematic asset and can be validated with official facility information and local geometry.
- Impact: Traffic volume and vehicle-level exposure modeling are deferred.

## D-008 Document Responsibilities

- Date: 2026-08-30
- Decision: Keep document roles separate.
- Files:
  - `README.md`: project entry and run instructions
  - `TODO.md`: current work and priority
  - `docs/PROJECT_PLAN.md`: planning and product direction
  - `docs/DEVELOPMENT_GUIDE.md`: implementation rules
  - `docs/DATA_GUIDE.md`: data acquisition and provenance rules
  - `docs/ARCHITECTURE.md`: system structure
  - `docs/DECISIONS.md`: design and data decisions
  - `docs/data-quality.md`: data-quality issues
- Impact: Avoid copying the same explanation into multiple documents.

## D-009 Official 2023 Building Layer

- Date: 2026-08-30
- Decision: Use MOLIT/VWorld `GIS Building Integrated Information` 2023-07 SHP as the authoritative building layer for the 2023 Osong analysis.
- Reason: OSM and official building data differ; the official 2023 dataset is more defensible as the analysis baseline.
- Impact: OSM 2023 building footprints are used as QA/cross-validation, with `MATCHED`, `OFFICIAL_ONLY`, and `OSM_ONLY` flags. OSM 2026 is excluded from 2023 incident analysis and kept only for current-state comparison.

## D-010 Osong Reconstruction Does Not Depend on Flood Extent First

- Date: 2026-08-31
- Decision: Treat the Osong case as an observed-event reconstruction based on rainfall, water level, incident timeline, levee events, and underpass inundation timing. Official Flood Extent is validation material, not the only starting point.
- Reason: The Osong disaster is strongly explained by hydromet observations and event timing even when an official vector flood extent is unavailable.
- Impact: Historical Replay and baseline/intervention logic can proceed, while final exposure geometry remains pending.

## D-011 Approximate Flood Envelope Classification

- Date: 2026-09-01
- Decision: Keep `approx_flood_envelope` as a temporary DEM-constrained derived approximation.
- Reason: It helps make Historical Replay spatially visible, but it is not a calibrated hydraulic model or official inundation boundary.
- Impact: The layer can be shown in the map as a reconstruction aid, but it cannot be used as official Flood Extent, depth, velocity, or final exposure KPI geometry.

## D-012 HAND Before Full Hydraulic Simulation

- Date: 2026-09-01
- Decision: The next spatial reconstruction improvement should evaluate HAND plus observed water level and DEM connectivity before introducing HEC-RAS/LISFLOOD-FP as project-critical MVP dependencies.
- Reason: HAND better matches the current reconstruction goal while staying lighter than full 2D hydraulics.
- Impact: HEC-RAS remains Phase 2, while Phase 1 focuses on observed reconstruction and defensible What-if comparison.

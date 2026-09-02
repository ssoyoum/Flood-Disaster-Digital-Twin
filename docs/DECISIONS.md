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
- Detail:
  - `approx_flood_envelope`
  - 기존 단순 근사 방식
  - Input: DEM low-elevation context, WAMIS river proximity, underpass proximity, incident timeline stage.
  - Method: already-low DEM cells are selected by stage thresholds and distance buffers.
  - Strength: simple, fast, easy to explain as a first MVP visualization.
  - Limit: it only starts from low-elevation cells, so it does not explicitly model relative height above drainage or drainage-connected terrain.
  - Status: retained as comparison and fallback visualization, not the preferred reconstruction layer.

## D-012 HAND Before Full Hydraulic Simulation

- Date: 2026-09-01
- Decision: The next spatial reconstruction improvement should evaluate HAND plus observed water level and DEM connectivity before introducing HEC-RAS/LISFLOOD-FP as project-critical MVP dependencies.
- Reason: HAND better matches the current reconstruction goal while staying lighter than full 2D hydraulics.
- Impact: HEC-RAS remains Phase 2, while Phase 1 focuses on observed reconstruction and defensible What-if comparison.
- Detail:
  - `hand_reconstruction`
  - 하천 연결성 + 상대고도 기반 개선 방식
  - Input: Copernicus DEM grid, WAMIS drainage geometry, HRFCO/Flood Control Office observed water-level time series, KMA rainfall context, Gungpyeong 2 underpass geometry, incident timeline stage.
  - Method: calculate a HAND-like relative elevation for each DEM grid cell against nearby WAMIS drainage-context cells, then filter cells by drainage connectivity, river-to-underpass flow corridor, and observed relative water-level rise by stage.
  - Core rule: HRFCO 관측 수위와 DEM 고도의 수직 기준이 직접 일치한다고 가정하지 않고, HAND 기반 상대고도와 관측 수위 변화량을 결합하는 방식으로 공간 재구성을 수행한다.
  - Why this is better than `approx_flood_envelope`: it uses all DEM grid cells, evaluates terrain relative to river/drainage context, and ties timeline expansion to observed water-level changes instead of using only broad low-elevation thresholds.
  - Limit: gauge datum is not converted to DEM vertical datum, so the output is not an absolute water-surface model, flood depth, velocity, or official Flood Extent.
  - Status: preferred Phase 1 reconstruction layer for map replay, still classified as `TEMPORARY` and `DERIVED_APPROXIMATION`.

## D-013 Reconstruction Envelope Comparison

- Date: 2026-09-01
- Decision: Show and document both `approx_flood_envelope` and `hand_reconstruction`, with `hand_reconstruction` enabled by default.
- Reason: The two layers explain model evolution. The first is a simple low-elevation approximation; the second is a more defensible drainage-relative reconstruction.
- Impact: Users can compare the old and improved reconstruction methods without mistaking either for official Flood Extent.
- Stage comparison:

| Stage | Time meaning | approx features | approx area km2 | HAND features | HAND area km2 | Interpretation |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| warning | Flood warning | 0 | 0.0000 | 0 | 0.0000 | No envelope shown before hydraulic threshold stage. |
| hydraulic_warning | Design flood level reached | 36 | 3.6275 | 278 | 28.0008 | HAND expands earlier because it considers drainage-relative low terrain, not only p25 low-elevation cells. |
| overtopping | Overtopping begins | 96 | 9.6726 | 341 | 34.3466 | HAND adds connected flood-prone terrain as observed water level rises. |
| levee_failure | Temporary levee failure | 182 | 18.3358 | 418 | 42.1027 | HAND reflects breach-stage connectivity toward the underpass corridor. |
| underpass_inflow | Underpass inflow starts | 241 | 24.2784 | 476 | 47.9448 | HAND shows broader potential connected terrain at the validation point. |
| unsafe_driving | Unsafe driving condition | 270 | 27.1991 | 508 | 51.1678 | HAND remains broader but still bounded by connectivity and HAND threshold. |
| full_inundation | Full inundation | 298 | 30.0194 | 540 | 54.3915 | HAND final envelope is larger, but still a derived reconstruction layer, not final inundation geometry. |

- Reading rule:
  - Larger HAND area does not mean verified larger flood damage.
  - It means the improved method identifies more terrain as drainage-connected and relatively low under the observed event progression.
  - Final exposure KPIs remain `PENDING_FLOOD_EXTENT` until official vector Flood Extent or calibrated hydraulic output is available.

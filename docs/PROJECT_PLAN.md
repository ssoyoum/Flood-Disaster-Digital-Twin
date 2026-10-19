# FloodOps Project Plan

Last updated: 2026-10-19

## Definition

FloodOps is a facility-centered flood monitoring and control-decision twin for places where rivers meet roads: underpasses and river access points. Low-lying evacuation areas are an expansion target once verified coordinates and evacuation criteria are available.

The product uses observed river levels and rainfall, official flood forecasts, and facility-specific evidence to screen risk. For facilities that pass operational data gates, it compares the control rule with historical observations and records a human operator's review. Historical event replays are validation and training material; the facility is the unit of operation.

Facilities have two evidence levels:

- **Watch:** a nearby river gauge or rainfall station supports a provisional risk rank. Gauge representativeness, local drainage, pumps, and the exact inundation path may be unknown. A watch rank is a screening signal, not a control recommendation.
- **Operational:** the facility has a reviewed inflow path, representative gauge, field measurement, and validation event in the registry. Its own rule can drive a control review, be backtested, and have operator confirmations recorded.

Official river flood forecasts may raise the minimum watch stage for river-driven facilities. Observed-rain thresholds support pluvial screening. Neither input proves that a specific facility is inundated.

FloodOps does not:

- issue an automatic closure or evacuation command
- claim a precise future flood time from a recent-rate calculation
- replace official flood maps or agency warnings
- claim validated depth, velocity, damage, or casualty reduction
- infer a facility's flood source from proximity alone

Core value:

> National facility screening + evidence-gated facility decisions + historical validation

## Reference Case

The primary validation case is:

> 2023 Osong Underpass Flood - Miho River and Gungpyeong 2 Underpass

Its historical evidence flow is:

```text
rainfall
-> Miho River water-level rise
-> overflow
-> temporary levee breach
-> underpass inflow
-> underpass risk-state change
-> response intervention timing
```

The reference case checks whether a facility rule would have raised a control review before the recorded underpass inflow. Other cases are scored against reported closure times with their source precision preserved. A replay result is not a claim that a different action would have prevented damage.

## Phase 1: Historical evidence and rule validation

**Status: complete for the current validation set.** This phase establishes observed data, sourced event milestones, replay, and measurable rule timing.

- Osong replay combines observed rainfall and water levels with the sourced incident timeline and provisional spatial layers.
- Official HRFCO flood forecast issuance is compared with observed stage and facility rules.
- A deterministic scorecard replays facility risk at 10-minute steps against reported control or inflow times for Osong and three Daejeon cases. Approximate and upper-bound news times retain their source precision.
- Closure-timing and inflow-delay scenarios compare timestamps only; they do not estimate avoided damage or casualties.

## Phase 2: National watch and facility decision twin

**Status: active.** The first operating view is the national watch board. The current risk API ranks 399 facilities by provisional driver: 144 river-driven and 255 pluvial. Only Gungpyeong 2 Underpass has an operational facility-specific rule; the remaining facilities are watch-level candidates.

- Live HRFCO water levels and rainfall are kept separate from historical replay. Repeated source timestamps do not count as new observations; source quality and age remain visible.
- River-driven facilities use the linked gauge stage, with an official flood advisory or warning as a minimum stage. Pluvial facilities compare nearby observed rainfall against KMA advisory amounts; the current KMA heavy-rain warning sets a live-only floor for pluvial and riverside facilities. Historical replay does not use the current warning feed.
- One-hour rainfall history is cached locally. Twelve-hour rainfall is shown only after 12 consecutive hourly observations exist.
- The operational facility view supports current status, rule criteria review, historical backtest, and local operator confirmation records. A record captures the server-side observation and rule snapshot and distinguishes live from replay.
- Watch-level estimates show their connected gauge or rainfall basis and limits. They do not become operational rules by being displayed or ranked.

## Phase 3: Evidence, coverage, and release readiness

**Status: planned and partly blocked by external data access.** Expand operational coverage only when the evidence gates can be checked for each facility.

- Obtain entrance low-point elevations, drainage or river inflow paths, field sensors, closure criteria, and time-stamped control histories from the responsible agencies.
- Add facilities only after registry gates for inflow path, representative gauge, field measurement, and validation event are documented. Keep unresolved sites as watch-level candidates.
- Approved KMA AWS minute rainfall and the current KMA warning feed are connected to live monitoring. Historical warning issuance (`wrn_met_data.php`) and ASOS hourly rainfall (`kma_sfctm2.php`) remain approval-gated for retrospective validation. Do not substitute unavailable historical data with fabricated or stale values.
- Deploy the updated board only after cloud access and deployment prerequisites are approved; confirm live/replay separation and the memory limit on the target server.
- Record agency interviews and pilot observations as evidence before changing facility rules or product claims.

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

## Historical Replay and Counterfactual Scope

Historical scenarios stay small and defensible.

Supported comparisons:

- facility closure at alternative times against recorded milestones
- user-specified delay to an observed milestone, with only the later timestamps shifted

Future sensitivity work may compare temporary barriers or levee conditions only when the assumed geometry and effect are explicit. A time shift is not a hydraulic effect.

Allowed outputs:

- lead time to recorded inflow or other milestones
- whether a closure time is before or after a recorded milestone
- shifted milestone timestamps under a user-defined delay
- baseline versus scenario timing comparison

Do not estimate deaths prevented, property damage avoided, or official damage reduction without a validated model and evidence.

## Hydraulic simulation research track

This track is separate from the operational watch board. Solver output remains `SIMULATED` until its inputs and results are checked against observed evidence.

Possible engines:

- HEC-RAS 2D
- LISFLOOD-FP

Research target:

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

HEC-RAS is a simulation engine, not the project identity. Do not present depth, velocity, or official flood extent until breach geometry, boundary conditions, facility elevations, and independent validation data are available. Automated warning or control commands are outside the current release scope.

## Future Case Expansion

Cases are validation material for facility rules, not the product unit. The current scorecard covers Osong 2023 and Daejeon 2020, 2023, and 2024. Additional cases remain conditional:

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

For the current release:

- live monitoring and historical replay are visibly distinct, with observation time, source quality, and stale-data behavior exposed
- each facility rank names its river or rain basis and says when that basis does not establish local flooding
- only a registry-approved facility receives an operational control-rule review
- official forecast, observed gauge/rainfall, facility rule, and reported control time remain separate evidence rows
- scorecards preserve the source precision of reported event times and show late, early, or missing signals without hiding adverse results
- operator confirmation records store the server observation/rule snapshot and label replay records as historical
- derived spatial layers remain labeled provisional; no unvalidated depth, velocity, exposure-loss, or casualty-reduction claim is shown
- release tasks include approved API access, target-server memory and mode checks, and a documented deployment endpoint

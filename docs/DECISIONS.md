# FloodOps Decisions

Last updated: 2026-09-06

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

## D-014 Exposure Inventory Before Envelope-Based Impact Metrics

- Decision: 침수 영향 지표를 envelope 공간중첩으로 산출하지 않는다. 대신 사건 초점 시설 기준 반경별 노출 재고(exposure inventory)를 산출한다. envelope은 시간에 따른 위험 확산 맥락으로만 유지한다.
- Context: DQ-008 검증 결과 HAND envelope이 stage 6에서 AOI의 51.4%를 덮고, 지하차도 500m 반경에서는 건물의 92.2%를 침수로 판정한다. DEM 해상도를 318m에서 28m로 높여도 이 비율이 개선되지 않았다. 지배적 레버는 connectivity distance이며 HAND 조건의 기여는 회랑을 좁힐수록 0에 수렴한다.
- Alternatives considered:
  - 경로 B: 선택 규칙을 재설계해 envelope을 좁힌 뒤 공간중첩 영향 지표를 산출한다. 공식 벡터 Flood Extent가 없어 어떤 파라미터가 옳은지 검증할 기준이 없다. connectivity 150m는 15.1%, 300m는 23.7%를 주지만 둘 중 무엇이 사실에 가까운지 판단할 근거가 없다. 검증 기준 없는 파라미터 조정은 근거 없는 튜닝이므로 채택하지 않는다.
  - AOI 클립만 적용하고 기존 영향 지표를 유지한다. AOI 내부 비율이 그대로여서 문제를 해결하지 못한다.
- Consequence:
  - 노출 재고는 공식 건물 대장, OSM 도로, OSM 시설 재고를 그대로 사용하므로 envelope 정확도에 의존하지 않는다.
  - 노출 재고는 침수 영향 추정이 아니다. "반경 안에 무엇이 있는가"이지 "무엇이 침수됐는가"가 아니라는 점을 API와 UI에서 명시한다.
  - 노출 KPI는 계속 PENDING_FLOOD_EXTENT로 유지한다.
  - 경로 B는 Safemap WMS raster 대조 검증 절차를 만든 뒤 재검토한다.

## D-015 A Refusal Must Offer an Answerable Question

- Date: 2026-09-06
- Decision: 등록된 도구로 답할 수 없는 요청은 거절하되, 응답에 답할 수 있는 질문 목록을 `suggestions`로 함께 반환한다. 시작 질문 칩과 거절 시 제안은 `GET /api/agent/examples` 한 곳을 출처로 쓴다.
- Reason: 거절만 하고 끝나면 사용자는 이 시스템이 무엇을 답할 수 있는지 알 방법이 없다. 또 칩 문구와 제안 문구를 따로 관리하면 UI가 권한 질문이 정작 거절당하는 상태로 갈라진다.
- Impact:
  - `UNSUPPORTED`는 전체 목록, `NEEDS_CLARIFICATION`은 감지된 후보 워크플로만, `READY`는 빈 배열을 반환한다.
  - 규칙 플래너와 LLM 플래너 두 경로 모두 같은 목록을 쓴다.
  - 칩 문구가 실제로 워크플로에 라우팅되는지를 테스트로 고정한다. 답할 수 없는 문구를 칩에 넣으면 테스트가 실패한다.

## D-016 Bound the LLM Planner and Fall Back to Rules

- Date: 2026-09-06
- Decision: LLM 의도 해석 요청에 명시적 timeout(기본 10초)과 재시도 0회를 적용한다. 실패하면 규칙 기반 플래너로 폴백하고, 폴백 사유를 응답 `planner_note`에 남긴다.
- Reason: SDK 기본값은 timeout 10분에 재시도 2회다. 네트워크가 불통이면 폴백이 도는 것이 아니라 요청 자체가 멈춘다. 폴백 로직이 있어도 도달하지 못하면 없는 것과 같다.
- Impact:
  - `AGENT_LLM_TIMEOUT_SECONDS`로 조정한다. 불통 주소를 향해 timeout 3초로 설정했을 때 3.4초 내에 규칙 플래너 결과가 반환되는 것을 확인했다.
  - 자격증명이 없거나 네트워크가 없는 환경에서도 서비스가 그대로 동작한다. 폐쇄망 적용의 전제이기도 하다.
  - LLM은 워크플로 선택과 파라미터 추출만 담당한다. 분석 수치는 어떤 경로에서도 결정론 도구 계층에서만 나온다.


# Data Quality Register

Last updated: 2026-09-02 23:20 KST

주요 데이터셋 또는 snapshot:
- 2023 Osong event data package
- DSSP-IF-00117 flood-mark inventory candidate check
- Safemap IF_0092_WMS flood-mark raster snapshot
- KMA AWS rainfall observation, 2023-07-14 through 2023-07-17 KST
- Flood Control Office water-level observation, 2023-07-14 through 2023-07-17 KST
- SGIS administrative boundary snapshot: 2023
- OSM historical snapshot: 2023-07-15
- Official GIS Building Integrated Information: 2023-07

Analysis scope:
- Representative case: 2023 Osong river and transport-facility flood, Miho River and Gungpyeong 2 Underpass
- Current phase: local processed data connection and pre-flood-extent validation
- Exposure calculations remain pending until official vector Flood Extent is available.

Current validation status:
- Official rainfall and water-level observations are connected as observed hydromet context.
- Osong is treated as an event reconstruction case driven by rainfall, water level, levee failure timing, and underpass inundation timing.
- Safemap flood marks are available as a WMS raster overlay only.
- DSSP flood-mark API access was validated, but no usable 2023 Osong vector record was confirmed from the inspected candidate inventory.
- Data vintage and event year are tracked separately.

Open data-quality issues count: 3

## Issues

### DQ-001: Safemap WMS flood marks are raster, not vector Flood Extent

- Status: Open
- Impact: High
- 발견일: 2026-08-31
- 대상 데이터셋: Safemap IF_0092_WMS flood-mark snapshot
- 증상: 오송 주변 침수흔적 WMS는 화면 표시용 PNG raster로 확보되었지만, 건물·도로·지하차도 중첩 계산에 바로 사용할 vector geometry가 아니다.
- 원인: Safemap 공개 예제는 WMS image response를 제공하며, 현재 확보한 산출물도 `image/png` snapshot이다.
- 분석 결과에 미치는 영향: 침수 건물 수, 침수 도로 길이, 노출 인구 등 geometry 기반 KPI를 VERIFIED 값으로 계산할 수 없다.
- 해결 방법: 공식 vector Flood Extent를 확보하거나, raster vectorization을 수행할 경우 파생 산출물로 별도 기록하고 원본 raster와 구분한다.
- 검증 방법: WMS 응답 content type, image dimension, nontransparent pixel count를 확인하고, vector feature count가 없음을 기록한다.
- 근거 코드/산출물 경로: `data/raw/flood_extent/osong/safemap_if_0092_wms/osong_bbox_4326_layers.png`, `backend/app/main.py`, `backend/app/osong_repository.py`, `data/processed/osong/validation_report.json`
- Residual risk / 남은 한계: WMS layer의 내부 갱신 기준과 개별 flood mark의 사건연도 속성은 image만으로 검증하기 어렵다.

### DQ-002: DSSP flood-mark candidate inventory has no confirmed 2023 Osong record

- Status: Open
- Impact: High
- 발견일: 2026-08-31
- 대상 데이터셋: DSSP-IF-00117
- 증상: 승인된 API로 inventory를 조회했지만 2023 오송 사건에 바로 연결 가능한 vector flood extent candidate가 확인되지 않았다.
- 원인: API inventory의 발생연도, 행정구역, geometry record가 오송 사건 요구 범위와 일치하지 않는다.
- 분석 결과에 미치는 영향: 사고 재현 자체를 막지는 않지만, 최종 침수범위 유사도 검증과 geometry 기반 노출 KPI는 보류된다. 현재 앱은 Flood Extent KPI를 `PENDING_FLOOD_EXTENT`로 유지해야 한다.
- 해결 방법: DSSP 다른 endpoint, portal export, 지자체 공식 침수흔적도, 또는 별도 공식 자료를 확보해 사건·공간·연도 일치 여부를 재검증한다.
- 검증 방법: `FLDN_YR`, 행정구역 코드, WKT geometry, processed candidate feature count를 확인한다.
- 근거 코드/산출물 경로: `data/scripts/validate_dssp_flood_extent_00117.py`, `data/scripts/inspect_dssp_osong_records.py`, `data/processed/osong/osong_dssp_if_00117_2023_candidates.geojson`, `data/processed/osong/dssp_osong_record_inspection.json`
- Residual risk / 남은 한계: 포털 갱신일과 원자료 사건연도는 다를 수 있으며, 같은 dataset id라도 공개 범위가 API와 웹 다운로드에서 다를 수 있다.

### DQ-003: Agency snapshots have different data vintages

- Status: Accepted limitation
- Impact: Medium
- 발견일: 2026-08-31
- 대상 데이터셋: SGIS administrative boundary, OSM historical layers, GIS Building Integrated Information, WorldPop, DEM, Safemap WMS
- 증상: 사건연도는 2023이지만, 각 레이어의 기준시점은 2023-07, 2023-07-15 snapshot, 2023 annual population, 2024 Safemap collection, DEM source vintage 등으로 서로 다르다.
- 원인: 기관별 데이터 생산·갱신주기와 snapshot 정책이 다르다.
- 분석 결과에 미치는 영향: 서로 다른 기관 레이어를 단일 사건 시점의 완전한 관측값처럼 해석하면 노출량과 시설 존재 여부가 과대 또는 과소 해석될 수 있다.
- 해결 방법: `event_year`, `data_vintage`, `boundary_snapshot`, `source_type`, `role`을 분리해 표시하고, 없는 기준연도는 `UNKNOWN` 또는 `NOT RECORDED`로 둔다.
- 검증 방법: manifest, processed metadata, API response의 vintage/status field를 비교한다.
- 근거 코드/산출물 경로: `data/manifests/source-availability.yml`, `backend/app/osong_repository.py`, `src/App.tsx`, `src/types.ts`
- Residual risk / 남은 한계: 일부 공개자료는 정확한 월별 snapshot 또는 객체별 갱신일을 제공하지 않아 완전한 시점 정합은 불가능할 수 있다.

### DQ-004: Rainfall and water-level observations require explicit temporal alignment

- Status: Accepted limitation
- Impact: Medium
- 발견일: 2026-08-31
- 대상 데이터셋: KMA AWS rainfall CSV, Flood Control Office water-level CSV
- 증상: 강우는 station별 시간 강수량이고 수위는 10분 단위 관측값이므로 직접 비교하려면 시간축, timezone, peak 기준을 명시해야 한다.
- 원인: 관측기관과 관측간격이 다르고, 강우 peak와 수위 peak는 물리적으로 지연될 수 있다.
- 분석 결과에 미치는 영향: 강우 -> 수위 -> 침수흔적 흐름 설명에서 peak 시각을 단순 동시 발생으로 해석하면 잘못된 causal narrative가 생길 수 있다.
- 해결 방법: KST 기준 timestamp를 유지하고, rainfall peak, water-level peak, primary station peak를 별도 field로 관리한다. Historical Replay와 rule-based intervention에서는 사건기록 시간을 기준으로 상태를 전환하고, 향후 lag 분석은 별도 derived 분석으로 기록한다.
- 검증 방법: processed CSV row count, station id, period, unit, peak timestamp를 확인한다.
- 근거 코드/산출물 경로: `data/processed/osong/osong_kma_aws_rainfall_2023-07-14_17.csv`, `data/processed/osong/osong_hrfco_water_level_10m_2023-07-14_17.csv`, `backend/app/osong_repository.py`, `src/App.tsx`
- Residual risk / 남은 한계: 수위 관측소와 궁평2지하차도 사이의 수리학적 전달시간은 현재 모델링하지 않았다.

### DQ-005: Incident timeline values require explicit source-page evidence

- Status: Investigating
- Impact: High
- 발견일: 2026-08-31
- 대상 데이터셋: Osong official investigation timeline, CCTV-derived inundation timing, KMA rainfall, Flood Control Office water level
- 증상: 사고 재현에는 04:10 홍수경보, 06:40 계획홍수위 29.02m 도달, 07:50 월류, 08:09 임시제방 붕괴, 08:27 지하차도 유입, 08:35 주행 곤란, 08:40 완전침수 같은 시간축이 핵심이지만, 현재 manifest에는 각 시간값의 공식 원문 page/path가 구조화되어 있지 않다.
- 원인: 기존 작업은 Flood Extent 확보 여부를 중심으로 정리되어 있었고, 사건 재현용 timeline evidence table을 별도로 만들지 않았다.
- 분석 결과에 미치는 영향: 시간값의 출처가 불명확하면 baseline 재현의 검증 기준과 narrative가 약해지고, 강우 -> 수위 -> 붕괴 -> 침수 진행의 인과 설명이 과장될 수 있다.
- 해결 방법: 공식 조사자료, CCTV 근거, 홍수경보 기록, 수위 관측 record를 timeline evidence table로 분리하고 각 항목에 timestamp, source, page/url, confidence, role을 기록한다.
- 검증 방법: 각 timestamp가 공식 문서 또는 원본 관측자료에서 재현 가능한지 확인하고, KST timezone과 관측간격을 함께 기록한다.
- 근거 코드/산출물 경로: `TODO.md`, `data/processed/osong/osong_kma_aws_rainfall_2023-07-14_17.csv`, `data/processed/osong/osong_hrfco_water_level_10m_2023-07-14_17.csv`
- Residual risk / 남은 한계: CCTV 기반 침수 진행 시각은 공개자료 접근 범위에 따라 직접 원본 검증이 제한될 수 있다.

### DQ-006: DEM-constrained approximate flood envelope is not official Flood Extent

- Status: Accepted limitation
- Impact: High
- 발견일: 2026-09-01
- 대상 데이터셋: `data/processed/osong/osong_approx_flood_envelope_timeline.geojson`
- 증상: 지도에서 시간에 따라 침수 영향권처럼 보이는 면이 표시되지만, 이는 공식 침수흔적도 벡터나 2D 수리모델 결과가 아니다.
- 원인: 2023 오송 공식 Flood Extent 벡터가 미확보된 상태에서, 강우·수위·DEM·하천·사건 시간축을 이용해 historical reconstruction visualization용 근사 envelope를 생성했다.
- 분석 결과에 미치는 영향: 사건 진행을 시각적으로 설명하는 데는 유용하지만, 실제 침수면적, 수심, 유속, 침수 건물 수, 노출 인구 같은 VERIFIED KPI 계산에는 사용할 수 없다.
- 해결 방법: API/UI/manifest에서 `TEMPORARY`, `DERIVED_APPROXIMATION`, `not official Flood Extent`, `not hydraulic simulation`을 명시하고, 공식 Flood Extent 또는 calibrated 2D hydraulics 결과가 확보되면 별도 검증 후 교체한다.
- 검증 방법: stage별 feature count, CRS, geometry type, 입력 파일 경로, rainfall/water-level provenance를 validation report에 기록하고 frontend build/backend tests로 API 연결을 확인한다.
- 근거 코드/산출물 경로: `data/scripts/create_osong_approx_flood_envelope.py`, `data/processed/osong/osong_approx_flood_envelope_timeline.geojson`, `data/processed/osong/osong_approx_flood_envelope_validation.json`, `backend/app/osong_repository.py`, `src/App.tsx`
- Residual risk / 남은 한계: 붕괴 단면, 유량, 배수 구조, 지하차도 내부 수심 변화가 모델링되지 않았으므로 공간 범위 신뢰도는 낮음~중간 수준으로 제한된다.

### DQ-007: HAND reconstruction uses relative water-level change, not absolute DEM water surface

- Status: Accepted limitation
- Impact: High
- 발견일: 2026-09-01
- 대상 데이터셋: `data/processed/osong/osong_hand_reconstruction_grid.geojson`, `data/processed/osong/osong_hand_flood_envelope_timeline.geojson`
- 증상: HAND-like envelope는 하천 대비 상대고도와 연결성을 사용하지만, HRFCO 관측 수위의 기준면을 DEM vertical datum으로 변환하지 않았다.
- 원인: 현재 확보한 수위 processed CSV에는 관측소 수위값과 위치는 있으나, 해당 수위를 DEM 해발고도 수면으로 환산할 gauge datum / rating / river cross-section 정보가 없다.
- 분석 결과에 미치는 영향: 수위값을 직접 DEM 고도와 비교한 실제 침수 수면으로 해석할 수 없다. 지도 결과는 시간별 위험공간 재구성용이며 실제 침수심·유속·면적 검증값이 아니다.
- 해결 방법: API/UI/manifest에서 `TEMPORARY`, `DERIVED_APPROXIMATION`, HAND-like reconstruction임을 명시한다. Phase 2에서는 gauge datum, breach geometry, discharge, roughness, drainage structure를 확보해 calibrated physical model과 비교한다.
- 검증 방법: HAND grid feature count, stage별 selected feature count, CRS, geometry type, stage별 observed water level, relative water-level rise, input file path를 validation report에 기록한다.
- 근거 코드/산출물 경로: `data/scripts/create_osong_hand_reconstruction.py`, `data/processed/osong/osong_hand_reconstruction_grid.geojson`, `data/processed/osong/osong_hand_flood_envelope_timeline.geojson`, `data/processed/osong/osong_hand_reconstruction_validation.json`, `backend/app/osong_repository.py`, `src/App.tsx`
- Residual risk / 남은 한계: 하천-저지대 연결성은 DEM grid와 WAMIS river geometry 기반의 근사이며, 실제 범람 유량·제방 붕괴 폭·배수시설·지하차도 내부 체적을 반영하지 않는다.

### DQ-008: Reconstruction envelope covers most of the AOI, so it cannot back absolute exposure counts

- Status: Open / blocks exposure-style impact metrics
- Impact: High
- 발견일: 2026-09-02
- 대상 데이터셋: `data/processed/osong/osong_hand_flood_envelope_timeline.geojson`, `data/processed/osong/osong_approx_flood_envelope_timeline.geojson`
- 증상: HAND final stage envelope 면적이 54.392 km2로 오송읍 AOI(40.557 km2)의 1.34배이며, AOI 내부로 클립해도 19.416 km2로 읍 면적의 47.9%를 덮는다. 첫 stage(`hydraulic_warning`, 06:40)에서 이미 28.001 km2다.
- 원인: envelope이 제방 붕괴 지점으로부터의 사건별 전파가 아니라 AOI 전역의 낮은 HAND 등급 지형 선택에 가깝다. 붕괴 지점 기준 연결 성분 제약과 AOI 클립이 적용되지 않았다.
- 분석 결과에 미치는 영향: 이 envelope으로 공간중첩을 수행하면 공식 건물 25,283동 중 11,591동(45.8%), OSM 도로 1,305.2 km 중 659.5 km(50.5%)가 영향으로 집계된다. approx envelope도 22.6% / 26.3%다. 2023년 오송 침수는 미호강 임시제방 붕괴 지점~궁평2지하차도 회랑에 집중된 사건이므로 이 절대 수치는 근거로 제시할 수 없다.
- 해결 방법: (1) 절대 카운트 대신 stage별 증분과 궁평2지하차도 중심 반경 제한 지표를 사용한다. (2) envelope 재생성 시 붕괴 지점 기준 연결 성분 제약과 AOI 클립을 적용한다. (2)는 기존 분석 로직 변경이므로 DECISIONS 기록 후 별도 branch에서 수행한다.
- 검증 방법: AOI 면적, stage별 envelope 면적, AOI 클립 면적, 건물/도로 교차 수를 EPSG:5179 투영에서 재계산해 비교한다.
- 근거 코드/산출물 경로: `data/processed/osong/osong_reconstruction_envelope_comparison.json`, `data/processed/osong/osong_sgis_admin_boundary_2023.geojson`, `data/scripts/create_osong_hand_reconstruction.py`
- Residual risk / 남은 한계: 공식 vector Flood Extent가 없어 축소된 envelope도 정답과 대조 검증할 수 없다. 노출 KPI는 계속 `PENDING_FLOOD_EXTENT`로 유지한다.

## Open issues / watchlist

- DSSP-IF-00117 또는 대체 공식 vector Flood Extent 확보 시 DQ-001, DQ-002를 재검증한다.
- 공식 조사자료 기반 event reconstruction timeline을 만들면 DQ-004, DQ-005를 함께 재검증한다.
- HAND reconstruction을 고도화할 때 gauge datum, breach geometry, discharge, drainage structure 확보 여부를 재검증한다.
- 다음 사건을 추가할 때 WMS raster를 vector Flood Extent처럼 사용하는 일이 없는지 확인한다.
- envelope 기반 공간중첩 지표를 노출할 때 DQ-008의 면적 비율을 함께 표시했는지 확인한다.
- 공식 건물통합정보와 OSM historical building QA에서 `MATCHED`, `OFFICIAL_ONLY`, `OSM_ONLY` 비율을 산출하면 별도 DQ issue 또는 validation metric으로 기록한다.
- SGIS 또는 공식 행정경계 snapshot이 변경되면 `event_year`와 `boundary_snapshot` 혼동 여부를 재검증한다.
- 강우·수위 신규 관측소를 추가하면 timezone, period, unit, aggregation interval을 다시 확인한다.


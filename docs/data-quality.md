# Data Quality Register

Last updated: 2026-10-03 KST

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
- 재검토 (2026-10-03): gauge datum은 있었다. 관측소 정보 XML의 미호강교 `gdt` 19.643 m로 수위를 국내 표고(인천만 평균해수면 기준)로 환산할 수 있다(계획홍수위 EL 29.023 m). 그래도 DEM과 절대 비교하지 않는 결론은 유지한다. 근거는 다음과 같다.
  - 기준면 차이: Copernicus DEM은 EGM2008(EPSG:3855) 기준이다. 국내 수직기준은 전지구 지오이드에서 43.4 cm 벗어나 있다(Jekeli·Yang·Kwon 2009, Newton's Bulletin 4, GPS/수준점 500점, 표준편차 18.5 cm). 원문에 뺄셈 방향이 없어 보정 부호는 확정하지 못했다.
  - DEM 정확도가 기준면 차이보다 훨씬 크다: 제품 사양 절대 수직정확도 < 4 m(LE90). 건물·구조물·식생을 포함한 DSM이고, 취득 시기는 2010-12~2015-01로 2023년 임시제방·교량 공사 상태를 담지 않는다.
  - 하천 수면은 편집값이다: 미호강교 주변 81×81셀에서 가장 많은 값이 18.5 / 18.0 / 19.0 m로 계단식 평탄화된 값이다. 관측소 영점표고 19.643 m보다 낮아 실제 수면으로 쓸 수 없다.
  - 지하차도 주변 7×7셀은 20.64~29.81 m(중앙값 26.36 m)로, 30 m 셀에 도로·옹벽·주변 구조물이 섞여 있다.
  - 정리: 0.43 m 보정을 해도 DEM 오차(수 m)와 하천 편집값 때문에 "EL 29.02 m 수면 아래 셀 = 침수"라는 비교는 근거가 되지 않는다. 절대 수면 비교는 LiDAR DTM(국토지리정보원 수치표고 등)과 국내 표고 기준 자료를 확보한 뒤에 한다.
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
- 검증 실행 결과 (2026-09-02): 기존 HAND 알고리즘을 그대로 두고 DEM 격자만 바꾼 4개 변형을 stage 6에서 비교했다.
  - V0 현재 40x32 클립 없음: 54.16 km2, AOI 대비 133.5%, AOI 건물 60.0%, 지하차도 500m 건물 99.5%
  - V1 40x32 + AOI 클립: 19.56 km2, AOI 대비 48.2%, AOI 건물 59.2%, 500m 건물 99.5%
  - V2 native 30m 클립 없음: 61.01 km2, AOI 대비 150.4%, AOI 건물 62.0%, 500m 건물 92.2%
  - V3 native 30m + AOI 클립: 20.83 km2, AOI 대비 51.4%, AOI 건물 62.0%, 500m 건물 92.2%
  - 결론 1: 해상도를 11배(318m -> 28m) 높여도 AOI 대비 비율이 48.2%에서 51.4%로 개선되지 않는다. 해상도는 과대추정의 원인이 아니다.
  - 결론 2: AOI 클립은 AOI 밖 침수 주장만 제거한다(133.5% -> 48.2%). 내부 비율은 바뀌지 않는다.
  - 결론 3: 30m 해상도는 국소 변별에만 기여한다. stage 4 기준 500m 반경 건물 비율이 99.5%에서 74.7%로 내려간다.
- 원인 분해 (V3, 30m, stage 6): 하천 1350m 이내 66.9%, flow corridor 660m 5.4%, 지하차도 1215m 11.4%, connectivity 합집합 69.0%, hand <= 5.54m 63.1%, 최종 교집합 51.6%. AOI가 미호강 범람원이라 두 조건 모두 구분력이 낮다. 30m HAND 값의 p50은 0.45 m다.
- 민감도: connectivity 150m에서는 hand 임계를 5.54 m에서 0.5 m로 11배 조여도 15.1%에서 15.0%로만 바뀐다. 지배적 레버는 connectivity distance이며, 현재 envelope은 실질적으로 하천 거리 버퍼에 가깝다.
- 채택 판정: AOI 클립은 채택한다. 30m 해상도 재계산은 선택 규칙을 고친 뒤 재평가한다. 선택 규칙 재설계는 공식 Flood Extent 또는 Safemap raster 대조 검증 절차가 마련된 뒤에만 착수한다. 검증 기준 없이 파라미터를 조이는 것은 근거 없는 튜닝이다.
- 재산출 (2026-10-03, 09-30 개선 HAND 기준): `data/scripts/compare_osong_reconstruction_envelopes.py`에 AOI 클립 면적과 건물·도로 중첩을 넣어 다시 만들 수 있게 했다.
  - 분모 정정: 건물·도로 파일은 오송읍보다 넓은 범위를 담고 있다(25,283동 중 AOI 안 9,748동, 1,305.2 km 중 AOI 안 368.1 km). 09-02의 45.8% / 50.5%는 클립하지 않은 envelope을 전체 건물·도로로 나눈 값이다. 같은 방식으로 approx final을 계산하면 22.6% / 26.3%가 그대로 재현된다.
  - HAND final stage: 35.458 km2(이전 54.392), AOI 클립 15.434 km2 = AOI의 38.1%(이전 V1 48.2%). AOI 안 건물 4,746동(48.7%), 도로 159.6 km(43.3%).
  - HAND 첫 stage(`hydraulic_warning`): AOI 클립 5.362 km2(13.2%), 건물 694동(7.1%), 도로 64.3 km(17.5%).
  - approx final stage: AOI의 36.2%, 건물 4,382동(45.0%), 도로 41.1%.
  - 판정: 면적은 줄었지만 final stage가 여전히 AOI 안 건물의 절반 가까이를 덮는다. 절대 노출 카운트로 쓸 수 없다는 결론은 바뀌지 않는다. Status를 유지한다.
  - 클립하지 않은 HAND final 기준(이전 방식): 건물 8,642동 / 25,283동(34.2%), 도로 388.4 km / 1,305.2 km(29.8%).
- 근거 코드/산출물 경로: `data/processed/osong/osong_reconstruction_envelope_comparison.json`, `data/processed/osong/osong_sgis_admin_boundary_2023.geojson`, `data/scripts/create_osong_hand_reconstruction.py`
- Residual risk / 남은 한계: 공식 vector Flood Extent가 없어 축소된 envelope도 정답과 대조 검증할 수 없다. 노출 KPI는 계속 `PENDING_FLOOD_EXTENT`로 유지한다.

### DQ-009: Official design-flood-level time (06:40) is 10 minutes earlier than the archived HRFCO record (06:50)

- Status: Accepted discrepancy / official time kept
- Impact: Medium
- 발견일: 2026-10-02
- 대상 데이터셋: `data/processed/osong/osong_hrfco_water_level_10m_2023-07-14_17.csv`, `data/raw/water_level/osong/hrfco_waterlevel_info.xml`, `backend/app/osong_repository.py`
- 증상: 국무조정실 감찰 결과 발표(2023-07-28, 보도 기준)는 "07-15 06:40 미호천교 수위가 계획홍수위 해발 29.02 m에 도달"이라고 한다. 저장소의 HRFCO 10분 자료에서 미호강교(3011665)는 06:40에 9.30 m(EL 28.943 m), 06:50에 9.38 m(EL 29.023 m)로, 계획홍수위에 처음 닿는 시각은 06:50이다.
- 기준면 확인: 관측소 정보 XML의 `gdt` 19.643 m + `pfh` 9.38 m = EL 29.023 m로 발표값 29.02 m와 일치한다. 따라서 차이는 기준면이 아니라 시각 쪽에 있다.
- 원인: 확인하지 못했다. 발표가 당시 실시간(검증 전) 자료를 썼고 보관 자료는 이후 보정됐을 가능성, 1분 단위 자료 기준일 가능성, 10분 자료의 timestamp 규약 차이가 후보지만 근거가 없어 판정하지 않는다.
- 분석 결과에 미치는 영향: timeline의 `hydraulic_warning` 단계와 HAND stage 1(관측 수위 9.30 m 사용)은 발표 시각을 따른다. 통제 요건 충족 시각을 관측 자료로 다시 계산하면 10분 늦어진다. closure-timing·inflow-delay 분석은 08:09 이후 시각만 쓰므로 영향이 없다.
- 해결 방법: timeline 시각은 사건 기록인 06:40으로 유지하고, 사건 설명에 관측 자료 기준 06:50과 두 시각의 수위값을 함께 적는다. 관측 자료로 시각을 덮어쓰지 않는다.
- 검증 방법: CSV에서 `station_id=3011665` 06:30~07:00 행을 읽어 9.20 / 9.30 / 9.38 / 9.47 m를 확인한다.
- Residual risk / 남은 한계: 감찰 결과 원문 PDF의 쪽수, 그리고 발표에 쓰인 수위 자료의 종류(실시간/보정, 1분/10분)를 확인해야 확정할 수 있다. `gdt`는 API 조회 시점 메타데이터라 2023년 당시 값과 같은지 확인하지 못했다.

### DQ-010: Seoul 2022 case mixes official traces, a later building snapshot, and press-reported times

- Status: Accepted limitation
- Impact: Medium
- 발견일: 2026-10-03
- 대상 데이터셋: `data/processed/seoul_2022/*`, `data/scripts/process_seoul_2022_dorimcheon.py`
- 증상: 서울 사례는 근거 수준이 다른 자료를 한 화면에 올린다. 침수범위는 공식 침수흔적도(관측)다. 건축물은 2026-08-09 스냅샷이다. 사건 시각은 강우계 임계(관측) 3개와 언론 보도 4개가 섞여 있다.
- 원인:
  - 2022년 시점 OSM 건물은 범위 안에 3,817동뿐이라 노출 집계에 쓸 수 없었다. 같은 범위의 공식 건물은 66,146동이다.
  - 2022년 당시 공식 건물 스냅샷은 확보하지 못했다.
  - 신림동 사고·재난문자 시각의 공식 원문을 찾지 못했다.
- 분석 결과에 미치는 영향:
  - 2026년 스냅샷을 사용승인일로 걸러도 2022~2026년에 철거된 건물은 빠진다. 사용승인일이 빈 10,659동은 포함했다.
  - 동작구청 강우계는 2022-08-08 23:12 이후 값이 없다(08-09 행 없음). 동작구 일 강수량 비교에서 과소로 보일 수 있다.
  - 공식 침수흔적도의 `damage_type`에 "교육부-학자금-특성화고(국공립)-특급지(서울)" 같은 입력 오류값이 1건 있다.
- 해결 방법: 화면과 API에 출처 등급(관측 / 언론 보도)을 단계마다 표시한다. 건축물 기준일과 필터 조건을 노출 패널에 적는다. 흔적도의 상세 주소(`F_ZONE_NM`)와 건축물 지번은 처리 단계에서 버린다.
- 검증 방법: `python data/scripts/process_seoul_2022_dorimcheon.py`를 다시 실행해 `seoul_dorimcheon_summary.json` 수치가 같은지 확인한다. `backend/tests/test_seoul_case.py`가 흔적 10,468건, 겹친 건축물 13,015동, 주소 필드 부재를 고정한다.
- Residual risk / 남은 한계: 침수흔적에는 시각이 없어 사건 단계별 공간 확산을 재생할 수 없다. 반사실 저류 계산의 면적은 bbox 면적(28.69 km2)이고 도림천 실제 유역면적이 아니다.

## Open issues / watchlist

- DSSP-IF-00117 또는 대체 공식 vector Flood Extent 확보 시 DQ-001, DQ-002를 재검증한다.
- 공식 조사자료 기반 event reconstruction timeline을 만들면 DQ-004, DQ-005를 함께 재검증한다.
- HAND reconstruction을 고도화할 때 gauge datum, breach geometry, discharge, drainage structure 확보 여부를 재검증한다.
- 다음 사건을 추가할 때 WMS raster를 vector Flood Extent처럼 사용하는 일이 없는지 확인한다.
- envelope 기반 공간중첩 지표를 노출할 때 DQ-008의 면적 비율을 함께 표시했는지 확인한다.
- 공식 건물통합정보와 OSM historical building QA에서 `MATCHED`, `OFFICIAL_ONLY`, `OSM_ONLY` 비율을 산출하면 별도 DQ issue 또는 validation metric으로 기록한다.
- SGIS 또는 공식 행정경계 snapshot이 변경되면 `event_year`와 `boundary_snapshot` 혼동 여부를 재검증한다.
- 강우·수위 신규 관측소를 추가하면 timezone, period, unit, aggregation interval을 다시 확인한다.


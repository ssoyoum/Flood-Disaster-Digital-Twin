# FloodOps TODO

Last Updated: 2026-08-31 13:05 KST

- 작업 완료·상태 변경 시 TODO.md와 WORKLOG.md의 완료 여부 및 현재 상태가 서로 모순되지 않도록 함께 동기화한다.

## In Progress

- [ ] 2023 오송 사건을 대표 분석 사건으로 완성
  - 기본 사건: `2023 오송 하천·교통시설 침수 · 미호강 · 궁평2지하차도`
  - 분석 흐름: `미호강·제방 → 범람 → 지하차도 → 차량·통행자`
  - 우선 분석 대상: 지하차도·교통시설
  - 현재 확보: 2023-07-15 OSM 공간 스냅샷, 2023년 인구 래스터, Copernicus DEM, SGIS 2023 오송읍 행정경계, NASA POWER 보조자료, 공식 사건 보고서, KMA AWS 강우 원본, HRFCO 10분 수위 원본, 2023-07 공식 건물통합정보, WAMIS 공식 국가하천/지방하천 SHP, Safemap 침수흔적도 WMS 스냅샷
  - 미확보: 2023 오송 실제 침수흔적도 벡터 record
- [ ] 오송 확보 원본 레이어와 과거자료 기반 분석값 연결
  - 실행 중 API를 호출하지 않고 승인 후 확보한 원본 응답을 스냅샷으로 사용
  - 인구는 공식 통계 우선순위와 `event_year`/자료 기준연도를 분리해 관리
  - WAMIS 하천망, DEM 저지대 컨텍스트, Safemap WMS 스냅샷은 원본/API/지도 연결 완료
  - KMA 강우와 HRFCO 수위 기반 관측 컨텍스트 분석 패널은 연결 완료
  - 공식 벡터 침수흔적도 확보 전까지 실제 노출 KPI는 `PENDING_FLOOD_EXTENT`로 유지

## To Do

### High Priority

- [ ] 2023 오송 실제 침수흔적도 record 확보
  - `DSSP-IF-00117` API 원본 전체 38,003건은 확보했으나 `FLDN_YR=2023` 후보 record는 0건
  - `FLDN_YR=2024`도 0건이며, 오송 AOI geometry 교차 후보 516건은 2012/2016/2017/2019/2020/2022 records로 확인됨
  - Safemap `IF_0092_WMS` 오송 bbox 스냅샷은 확보 및 지도 연결 완료했으나 raster image이므로 정밀 중첩분석용 벡터로 취급하지 않음
  - 포털의 다른 승인 URL, 파일 export, 또는 별도 지자체/행안부 자료에서 2023 오송 실제 Flood Extent record를 추가 확인
  - 실제 벡터 record 확보 전까지 앱의 노출 KPI는 `PENDING_FLOOD_EXTENT` 유지
- [ ] 오송 침수흔적도와 건물·도로·궁평2지하차도 중첩 분석
  - 침수 건물 수, 침수 도로 길이, 지하차도 포함 여부를 실제 geometry로 계산
- [ ] 2023 오송 공식 읍면동·세부 공간인구 확보
  - 우선순위 1: 통계청/SGIS 등 한국 공식 세부 공간인구
  - 우선순위 2: 공식 읍면동 전체 인구 + WorldPop 공간분포 보정
  - 오송읍 전체 인구와 지역별 비교값은 공식 통계만 사용
  - `event_year: 2023`과 인구자료 기준연도를 manifest에 별도 기록
- [ ] WorldPop 2023 인구를 오송 사건 격자 집계에 연결
  - 공식 세부격자 인구가 없을 때만 공식 읍면동 인구의 공간분포 보정에 사용
  - WorldPop 단독 사용은 공식 인구자료 확보가 불가능할 때의 fallback으로 제한
  - Flood Extent 내부 공간분포 추정 결과만 `DERIVED`로 표시
- [ ] 미호강 공식 하천망 기반 분석과 행정경계 보강
  - 공식 하천 공간자료: WAMIS 국가하천/지방하천 SHP 원본 확보, 오송 AOI subset, API/지도 연결 완료
  - 공식 행정경계: SGIS 2023 오송읍 경계 원본 확보, EPSG:4326 processed 변환, API AOI 연결 완료
  - OSM 하천망은 공식 하천망과의 비교·검증 보조자료로 유지
  - 공식 Flood Extent 확보 후 하천 polygon과 침수흔적도·도로·지하차도 관계 분석
  - `event_year`와 `boundary_snapshot`을 별도 필드로 기록
  - 범람 원인과 읍·면·동별 집계에 사용

### Medium Priority

- [ ] 오송 2023 직접 피해·구호 record 추가 확인
  - `DSSP-IF-10175` 원본 전체 48,050건은 확보했으나 2023 청주/오송 후보 record는 0건
  - `DSSP-IF-10184` 원본 전체 39,188건에서 2023년 7월 청주 `4311*` 후보 22건, 오송 관련 텍스트 hit 9건 확인
  - `DSSP-IF-10184`는 geometry가 없는 구호상황 보고자료이므로 Flood Extent 대체자료로 사용하지 않음
  - 포털의 다른 승인 URL, 파일 export, 또는 지자체 사건 보고서에서 오송 직접 피해·침수 geometry record를 확인
- [ ] 네 가지 API 자료의 과거 스냅샷 검증·정규화
  - API 승인 후 원본 응답, 요청 시각, 데이터 연도, 응답 스키마, SHA-256을 manifest에 기록
  - 애플리케이션 실행 중 API를 매번 호출하거나 실시간 반영하지 않음

- [ ] 오송 사건 강우·수위·DEM·인구·침수흔적도 provenance 화면 추가
- [ ] 사건별 데이터 연도와 취득일을 레이어 상세 화면에 표시
- [ ] 궁평2지하차도와 도로 통제 분석을 별도 시설 타입으로 모델링
- [ ] 전국 사건의 AOI별 원본 데이터 검색·다운로드 파이프라인 구축
- [ ] 실제 공간 분석 결과를 Baseline/What-if API에 연결
- [ ] API 키 미입력, 응답 없음, 사건 데이터 없음 상태의 테스트 추가
- [ ] Playwright E2E로 오송 기본 진입·사건 전환·API 설정 흐름 검증

### Low Priority

- [ ] 긴급재난문자 `DSSP-IF-00247` 원본 확보
  - 사건 당시 경보·대피 안내의 발송 시각과 대상 지역 확보
  - 문자 발송 이력은 Historical Replay와 타임라인 검증용 스냅샷으로만 사용

- [ ] 2022 서울·2022 포항·2024 익산·2026 안동·의성 비교 분석
- [ ] DEM 기반 흐름 방향 파생 레이어
  - 저지대 컨텍스트 레이어는 생성 및 API/지도 연결 완료
  - 흐름 방향·집수 경로 분석은 별도 수문 지형 처리 단계에서 수행
- [ ] 매년 프로젝트 갱신 시 네 가지 API를 재신청·재다운로드하고 과거 스냅샷을 추가
- [ ] Vector Tile/PMTiles/COG 및 AOI Bounding Box 조회 최적화
- [ ] Historical Replay와 WebSocket 이벤트 재생
- [ ] PostGIS 스키마·Alembic migration 및 배치 적재
- [ ] HEC-RAS 또는 LISFLOOD-FP 결과 연동

### Future Ideas

- [ ] 공식 vs OSM 건물 일치율 QA 지표
  - 공간 매칭 결과를 `MATCHED`, `OFFICIAL_ONLY`, `OSM_ONLY`로 분류
  - QGIS 색상 예: `MATCHED` 초록, `OFFICIAL_ONLY` 보라, `OSM_ONLY` 주황
  - 포트폴리오 설명: authoritative 2023 official building layer와 OSM historical footprints를 자동 병합하지 않고 검증 플래그로 보존

- [ ] 궁평2지하차도 사후 설치 안전시설 What-if 시나리오 확장
  - 대상 시설: 수위센서 + 자동 진입차단시설, 차수시설
  - `BASELINE` (2023 당시 상태): 범람 → 지하차도 진입 가능
  - `INTERVENTION`: 수위센서·자동 진입차단시설 또는 차수시설을 메타데이터로 적용
  - `Scenario A`: 수위 감지 → 자동 진입차단
  - `Scenario B`: 차수시설 → 유입량 감소
  - 충북도 자료의 최저점 침수심 15cm 자동작동 기준은 공식자료로 재검증한 뒤 시나리오 파라미터로 사용
  - 이번 MVP에서는 시설 효과 계산, 차량 노출 추정, 교통량 모델링을 구현하지 않음

## Completed

### 2026-08-30

- [x] 기본 대표 사건을 `osong-2023`으로 변경하고 5개 사건 카탈로그를 유지
- [x] 사건 선택 시 사건별 Flood Extent, 타임라인, 공간 레이어, Baseline을 다시 조회
- [x] 오송 Copernicus DEM GLO-30 원본 확보
  - 타일: `N36_00_E127_00`
  - 제품 고도 자료 취득 기간: 2011-2015
  - 파일 객체 수정일: 2022-05-09
- [x] WorldPop Korea 2023 100m 인구 원본 확보
- [x] 오송 OSM 원본 확보
  - 조회 범위: `[36.58, 127.27, 36.68, 127.40]`
  - 대상: 건물, 도로, 하천, 시설, 지하차도
- [x] 오송 OSM geometry 보존 processed 데이터 생성 및 검증
  - `data/processed/osong/`에 건물 폴리곤, 도로, 하천, 시설, 터널 GeoJSON 생성
  - geometry type, validity, feature count, CRS `EPSG:4326` 검증
- [x] WAMIS 국가하천/지방하천 SHP 원본 확보 및 오송 AOI subset 생성
  - 원본: `data/raw/river/wamis_river_network/ntn_rvr.zip`, `data/raw/river/wamis_river_network/lcl_rvr.zip`
  - 결과: `data/processed/osong/osong_wamis_rivers.geojson`
  - 검증: raw Polygon, `EPSG:5179`; processed 8개 Polygon/MultiPolygon, `EPSG:4326`
- [x] WAMIS 공식 하천망을 Backend/API/MapLibre 레이어에 연결
  - `waterways` API 레이어를 OSM 2023 하천선에서 WAMIS 공식 하천 polygon으로 교체
  - 지도는 하천 polygon fill/outline과 하천명 popup을 표시
  - KPI `waterway_count`는 WAMIS 오송 subset 8개 기준으로 표시
- [x] Copernicus DEM 저지대 지형 컨텍스트 processed 생성 및 연결
  - 결과: `data/processed/osong/osong_dem_elevation_grid.geojson`, `data/processed/osong/osong_dem_low_elevation_context.geojson`
  - 오송 AOI p25 기준 `30.03m` 이하 303개 셀을 `LOW_ELEVATION_CONTEXT`로 표시
  - 침수 범위가 아닌 지형 설명용 레이어로 API/지도/Provenance에 연결
- [x] KMA AWS 강우 관측 timeline API 연결
  - `/api/events/osong-2023/flood/timeline`을 NASA 데모값에서 KMA AWS processed 144 rows로 교체
  - 관측소: 청주금천 `327`, 오창가곡 `977`, 단위 `mm`
- [x] HRFCO/Flood Control Office 10분 수위 원본 확보 및 processed 정규화
  - 원본: `data/raw/water_level/osong/hrfco_waterlevel_info.xml` 및 3개 지점 10분 수위 XML
  - 관측소: 청주시(팔결교) `3011635`, 청주시(미호강교) `3011665`, 세종시(미호교) `3011685`
  - 기간: 2023-07-14 00:00 through 2023-07-17 00:00 KST
  - 결과: `data/processed/osong/osong_hrfco_water_level_10m_2023-07-14_17.csv`, 1,299 rows, 단위 `m`
- [x] SGIS 2023 공식 오송읍 행정경계 원본 확보 및 AOI 연결
  - 원본: `data/raw/admin_boundary/sgis_2023/sgis_boundary_2023_chungbuk_sgg.geojson`, `data/raw/admin_boundary/sgis_2023/sgis_boundary_2023_33043_emd.geojson`
  - 오송읍 코드: `33043110`
  - 결과: `data/processed/osong/osong_sgis_admin_boundary_2023.geojson`, 1개 Polygon
  - SGIS 원본 좌표 `EPSG:5179`를 processed에서 `EPSG:4326`으로 변환하고 Backend AOI 레이어에 연결
- [x] 행정안전부 침수흔적도 `DSSP-IF-00117` API 원본 전체 확보 및 오송 2023 부재 검증
  - 원본: `data/raw/flood_extent/osong/dssp_if_00117_pages/`, 39 pages, 38,003 records
  - 응답: `resultCode=00`, geometry field `GEOM`, WKT, raw CRS 추정 `EPSG:3857`
  - 검증 결과: `FLDN_YR=2023` record 0건, 청주시 `43113`의 2023 candidate 0건
  - 후보 processed: `data/processed/osong/osong_dssp_if_00117_2023_candidates.geojson`, 0 features
- [x] Safemap 침수흔적도 WMS 스냅샷 확보 및 MapLibre overlay 연결
  - 원본: `data/raw/flood_extent/osong/safemap_if_0092_wms/osong_bbox_4326_layers.png`
  - 출처: 생활안전지도 `IF_0092_WMS`, layer `A2SM_FLUDMARKS`, 수집일 2024
  - 검증: 1024x1024 PNG, 296,634 bytes, 비투명 픽셀 146,863
  - 용도: 시각 검증용 Hazard overlay이며 벡터 Flood Extent 또는 노출 KPI 계산 입력으로 사용하지 않음
- [x] KMA 강우·HRFCO 수위 기반 오송 관측 컨텍스트 분석 패널 연결
  - API summary에 강우 피크, 강우 피크 시각/관측소, 최고수위, 미호강교 최고수위 시각을 추가
  - Frontend에 `Observed Hydromet` 패널을 추가해 `강우 → 하천 수위 → Safemap 침수흔적` 흐름을 표시
  - 벡터 Flood Extent 미확보 상태이므로 노출 인구·침수 건물·침수 도로 정량 KPI는 계속 `PENDING_FLOOD_EXTENT`
- [x] 피해침수 `DSSP-IF-10175` API 원본 전체 확보 및 오송 2023 부재 검증
  - 원본: `data/raw/damage_flood/osong/dssp_if_10175_pages/`, 49 pages, 48,050 records
  - 검증 결과: 2023 청주시/오송 후보 0건
  - 후보 processed: `data/processed/osong/osong_damage_flood_2023_candidates.json`, 0 records
- [x] 재해구호상황보고 `DSSP-IF-10184` API 원본 전체 확보 및 오송 2023 후보 검증
  - 원본: `data/raw/relief_report/osong/dssp_if_10184_pages/`, 40 pages, 39,188 records
  - 검증 결과: 2023년 7월 청주 `4311*` 후보 22건, 오송 관련 텍스트 hit 9건
  - 후보 processed: `data/processed/osong/osong_relief_report_2023_candidates.json`, 22 records
- [x] 오송 사건일 기준 OSM historical snapshot 확보 및 processed 데이터 생성
  - 요청 시점: `2023-07-15T23:59:59Z`
  - 건물 2,859개, 도로 6,727개, 하천 147개, 시설 386개, 터널 95개
  - 응답 DB timestamp는 별도로 기록하고 사건 스냅샷 날짜와 혼동하지 않음
- [x] 오송 행정경계 원본 및 AOI subset 확보
  - `event_year: 2023`, `boundary_snapshot.ADM1: 2023`, `boundary_snapshot.ADM2: 2020`을 분리 기록
  - 사건연도 또는 가장 가까운 연도의 경계를 우선하는 정책을 manifest에 기록
  - 원본 2종과 AOI subset 2종을 매니페스트에 기록
- [x] 오송 NASA POWER 시간별 강수 원본 및 processed CSV 확보
  - NASA POWER 원본: 2023-07-15~16, 48개 시점, `PRECTOTCORR`, `source_type: REANALYSIS`, `raw_status: VERIFIED`
  - 프로젝트용 processed CSV 변환본만 `processed_status: DERIVED`
- [x] 오송 공식 사건 보고서 원본 PDF 및 텍스트 추출본 확보
  - CODIL 보고서 93쪽, `미호강`·`궁평` 텍스트 추출 검증
- [x] 오송 MVP 핵심 교통시설 `궁평2지하차도` 시설 레이어 생성
  - 공식 검증: 시설명 `궁평2지하차도`, 노선 `지방도 508호선`, 관리기관 `충청북도도로관리사업소`
  - 2023-07-15 OSM historical snapshot의 way 2개를 `MultiLineString` 1개 피처로 결합
  - 결과: `data/processed/osong/gungpyeong2_underpass.geojson`, `EPSG:4326`, SHA-256 manifest 기록
  - 추가 교통량 모델링·차량 노출 추정은 MVP 범위에서 제외
- [x] KMA AWS/ASOS 강우 원본 확보
  - 원본: `data/raw/rainfall/osong/OBS_AWS_TIM_20260830132752.csv`
  - 관측소: 청주금천 `327`, 오창가곡 `977`
  - 기간: 2023-07-14 01:00 through 2023-07-17 00:00 KST
  - 검증: 144 rows, 강수량 단위 `mm`, CP949 원본
- [x] 국토교통부 `GIS건물통합정보` 2023-07 원본 확보
  - 충북: `data/raw/building_integrated/vworld_gis_building_integrated_2023-07-12_chungbuk/AL_43_D010_20230712.zip`
  - 충남: `data/raw/building_integrated/vworld_gis_building_integrated_2023-07-12_chungnam/AL_44_D010_20230712.zip`
  - 검증: SHP Polygon, `Korean_1985_Modified_Korea_Central_Belt`, 원본 ZIP 보존
- [x] 공식 `GIS건물통합정보` 2023-07 SHP processed 변환
  - 결과: `data/processed/osong/osong_official_buildings_2023.geojson`
  - 오송 AOI 교차 기준 25,283개 Polygon, `EPSG:4326`
  - 충남 원본은 보존했으나 현재 오송 AOI와 교차하는 feature는 0개
- [x] 공식 건물통합정보 × OSM 2023 건물 QA 매칭
  - 결과: `data/processed/osong/osong_building_qa_official_osm_2023.geojson`
  - QA summary: `MATCHED` 1,251, `OFFICIAL_ONLY` 24,032, `OSM_ONLY` 1,817
  - OSM 2026은 2023 사건 분석에서 제외
- [x] KMA AWS/ASOS 강우 원본 processed 정규화
  - 결과: `data/processed/osong/osong_kma_aws_rainfall_2023-07-14_17.csv`
  - 청주금천 `327`, 오창가곡 `977`, 총 144 rows, 단위 `mm`
- [x] 재난안전데이터공유플랫폼 서비스 키 입력·연결 테스트 UI 구현
- [x] 서울 2022 공식 침수흔적도 19,881개 피처의 API 연결

## Manual Action Required

사용자가 직접 제공하거나 공식 사이트에서 수동 다운로드해야 하는 데이터입니다. 새 데이터 출처를 추가하라는 뜻이 아니라, 이미 확인한 공식 출처가 인증/승인/수동 다운로드 단계에 있어 대기 중이라는 의미입니다.

- [ ] 행정안전부 재난안전데이터공유플랫폼 API 승인 후 원본 응답 저장
  - 상태: `BLOCKED_BY_API_APPROVAL`
  - 대상: `DSSP-IF-00247`
  - 승인 및 service key 발급 후 사건 기간/지역 기준으로 1회 원본 응답을 저장

## Known Issues

- [ ] 오송 Flood Extent는 현재 사건 위치 기반 임시 폴리곤이며 관측 침수흔적도가 아님
- [ ] `DSSP-IF-00117` 원본 API는 정상 응답을 확보했지만 2023 오송/청주 후보 record가 없어 실제 Flood Extent로 연결하지 않음
- [ ] `DSSP-IF-10175` 원본 API는 정상 응답을 확보했지만 2023 오송/청주 후보 record가 없어 직접 피해침수 record로 연결하지 않음
- [ ] `DSSP-IF-10184` 원본 API에는 2023년 7월 청주/오송 구호상황 후보가 있으나 geometry가 없는 보고자료이므로 Flood Extent로 대체하지 않음
- [ ] `DSSP-IF-00247` 긴급재난문자는 현재 available key set에서 `SERVICE_ACCESS_DENIED`
- [ ] 공식 세부 공간인구는 아직 확보 전이며, 공식 읍면동 인구는 확보됨. WorldPop은 fallback 공간분포 자료로만 사용
- [ ] DEM 저지대 컨텍스트는 연결 완료, 흐름 방향·집수 경로 분석은 미구현
- [ ] OSM 건물과 Facilities/POI는 같은 OSM 원본에서 분리한 별도 레이어이며, 같은 장소에서 겹칠 수 있음
- [ ] OSM Buildings는 건물 폴리곤이고 Facilities/POI는 `amenity` 등 점 객체라 아직 conflation/중복제거를 하지 않음
- [ ] OSM 2026-08-30 스냅샷은 2023 오송 당시 분석에서 제외하고, 추후 현재 비교용 데이터로만 검토
- [ ] 공식 건물 분석 데이터는 processed 변환과 OSM QA 플래그 생성까지 완료됐지만, 공식 침수흔적도와의 중첩 계산은 아직 미완료
- [ ] NASA POWER 강수는 재분석 자료이며 실제 관측소 강우량을 대체하지 않음
- [ ] geoBoundaries ADM2는 SGIS 2023 공식 오송읍 경계 확보 이후 fallback/reference로만 유지
- [ ] 오송 AOI OSM 행정경계 쿼리는 서버 timeout으로 확보하지 못해 geoBoundaries로 대체함
- [ ] 전국 침수흔적도는 후보 데이터셋만 확인했으며 오송 record 다운로드는 미완료

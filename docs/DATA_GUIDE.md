# FloodOps Data Guide

## 기준일과 연도 정책

이 디렉터리는 관측·파생·시뮬레이션 데이터를 분리해 보관한다. 파일을 내려받은 날짜와 데이터가 나타내는 사건 연도는 다를 수 있다.

- `data_year`: 관측 또는 사건이 발생한 연도
- `source_updated_at`: 원천 포털에 표시된 마지막 수정일
- `acquired_at`: 이 저장소에 파일을 확보한 날짜
- `snapshot_date`: OSM처럼 계속 바뀌는 데이터의 조회 시점
- DEM의 `acquisition_period`와 객체 수정일은 사건 연도와 별도로 기록한다

대표 분석 사건은 `data/manifests/event-catalog.yml`의 `default_event_id`로 관리하며 현재 `osong-2023`이다.

| 사건 | 지도 테마 | 핵심 분석 대상 | 현재 상태 |
| --- | --- | --- | --- |
| 2023 오송 | 2023 Osong Underpass Flood — Miho River | 지하차도·교통시설 | 대표 사건, 침수흔적도·수위 API 대기 |
| 2022 서울 | 2022 Seoul Urban Flood — Gangnam & Sillim | 반지하·지하공간 | 공식 침수흔적도 연결 |
| 2022 포항 | 2022 Pohang Typhoon Flood — Naengcheon | 산업시설 | 카탈로그 등록 |
| 2024 익산 | 2024 Iksan Extreme Rainfall Flood — Hamra | 농경지 | 카탈로그 등록 |
| 2026 안동·의성 | 2026 Andong–Uiseong Compound Flood — Gwimi & Gugye | 임시주거·산불피해지역 | 카탈로그 등록 |

## 공통 데이터 우선순위

1. 침수흔적도: 침수 범위 확인
2. 건물 폴리곤: 침수 건물 수 계산
3. 인구: 노출 인구 계산
4. 도로망: 침수 도로 길이 계산
5. 하천망·행정경계: 범람 원인과 지역별 집계
6. DEM·강우량: 저지대·흐름·사건 원인 설명
7. 중요시설 POI: 병원·학교·대피소 등 취약 시설 확인

건물 공식자료는 `건축물대장 SHP`로 부르기보다 국토교통부 `GIS건물통합정보` 또는 `건물통합정보` 명칭을 사용한다. 이 자료는 수치지형도 건물 공간정보와 세움터 건축물대장 속성정보를 건물 단위로 통합한 SHP 계열 자료로 취급한다. 오송 사건용으로 확보할 때는 사건 발생월인 `2023-07` 데이터를 우선한다.

오송 2023 건물 분석은 공식 2023 `GIS건물통합정보` SHP를 기준 건물 레이어로 둔다. OSM 2023 건물 footprint는 공식 데이터와의 공간 매칭 및 누락 의심 객체 확인용 보조 검증 레이어로만 사용한다. OSM 2026 스냅샷은 2023 당시 분석에서 제외하고, 추후 현재 상태 비교가 필요할 때만 별도 비교 레이어로 검토한다.

공식 건물과 OSM 건물은 자동 병합하지 않는다. 공간 매칭 결과는 `MATCHED`, `OFFICIAL_ONLY`, `OSM_ONLY` 품질검사 플래그로 남긴다.

## 하천망 확보 지침

하천 공간자료는 가능하면 공식 또는 준공식 하천망 SHP를 우선 사용하고, OSM 하천은 비교·검증 보조자료로 둔다. 오송 작업에서 확인한 최적 경로는 WAMIS 자료실의 국가하천/지방하천 첨부 ZIP이다.

1. WAMIS 자료실 `seq=621` 페이지에서 첨부 목록을 확인한다.
2. `/main/data_files.do`에 `pdssn=621`로 파일 목록을 확인한다.
3. `ntn_rvr.zip`은 국가하천, `lcl_rvr.zip`은 지방하천 원본으로 `data/raw/river/wamis_river_network/`에 그대로 저장한다.
4. 원본 ZIP의 크기, SHA-256, feature count, geometry type, CRS를 검증한다.
5. 사건 AOI bbox 또는 사건 경계로 subset하고 `EPSG:4326` GeoJSON을 `data/processed/<event_id>/`에 생성한다.
6. 하천명 한글은 콘솔 표시가 아니라 UTF-8 파일 바이트와 GeoJSON 값으로 검증한다. Windows PowerShell 기본 출력에서는 한글이 깨져 보일 수 있으므로 `PYTHONIOENCODING=utf-8` 또는 파일 직접 검증을 사용한다.

VWorld의 `국가기본도 하천중심선`, `국가기본도 실폭하천`, `국가기본도 하천경계`는 공식 후보 자료지만 비로그인 직접 다운로드에서는 실제 ZIP이 내려오지 않을 수 있다. 로그인 또는 수동 다운로드가 필요한 경우 `MANUAL_DOWNLOAD_REQUIRED`로 기록하고, 자동 우회나 세션 재현을 구현하지 않는다.

## 오송 2023 확보 자료

사건 공간 범위는 오송·궁평2지하차도·미호강 주변을 포함하는 `[36.58, 127.27, 36.68, 127.40]`이다.

| 데이터 | 데이터 연도/기준 | 저장 파일 | 상태 |
| --- | --- | --- | --- |
| DEM | 정적 자료, TanDEM-X 취득 기간 2011-2015; N36/E127 객체 수정일 2022-05-09 | `data/raw/copernicus_dem_glo30/Copernicus_DSM_COG_10_N36_00_E127_00_DEM.tif` | 확보 |
| 인구 | 2023, WorldPop Korea 100m R2025A v1 | `data/raw/worldpop/kor_pop_2023_CN_100m_R2025A_v1.tif` | 확보 |
| 공식 건물통합정보 | VWorld 충청북도 전체데이터 기준일 2023-07-12 | `data/raw/building_integrated/vworld_gis_building_integrated_2023-07-12_chungbuk/AL_43_D010_20230712.zip` | 확보 |
| 인접 공식 건물통합정보 | VWorld 충청남도 전체데이터 기준일 2023-07-12 | `data/raw/building_integrated/vworld_gis_building_integrated_2023-07-12_chungnam/AL_44_D010_20230712.zip` | 확보 |
| 공식 건물 processed | 오송 AOI 교차 subset, EPSG:4326 | `data/processed/osong/osong_official_buildings_2023.geojson` | 25,283개 Polygon |
| 공식 건물 × OSM QA | 공식 2023 건물과 OSM 2023 footprint 교차 매칭 | `data/processed/osong/osong_building_qa_official_osm_2023.geojson` | `MATCHED`/`OFFICIAL_ONLY`/`OSM_ONLY` |
| WAMIS 하천망 | 데이터 기준시점 미기록, WAMIS 국가하천/지방하천 SHP | `data/raw/river/wamis_river_network/ntn_rvr.zip`, `data/raw/river/wamis_river_network/lcl_rvr.zip` | 원본 확보 |
| WAMIS 하천망 processed | 오송 AOI bbox 교차 subset, EPSG:4326 | `data/processed/osong/osong_wamis_rivers.geojson` | 8개 Polygon/MultiPolygon |
| OSM 건물 검증 레이어 | OSM historical snapshot 2023-07-15 | `data/raw/osong/osm_context_2023-07-15.json` | 공식 건물 QA 보조 |
| OSM 2026 현재 비교 후보 | OSM 조회 스냅샷 2026-08-30 | `data/raw/osong/osm_context_2026-08-30.json` | 2023 분석 제외 |
| 침수흔적도 | 2023 오송 사건 record | 재난안전데이터공유플랫폼 API/다운로드 예정 | 미확보 |
| 강우 | KMA AWS 2023-07-14 01:00 through 2023-07-17 00:00 KST | `data/raw/rainfall/osong/OBS_AWS_TIM_20260830132752.csv` | 확보 |
| 강우 processed | KMA AWS 원본 정규화, UTF-8 CSV | `data/processed/osong/osong_kma_aws_rainfall_2023-07-14_17.csv` | 144 rows |
| 수위 | 2023-07-15 사건 시간창 | 재난안전데이터공유플랫폼·수문 관측 API 예정 | 서비스 키 대기 |

## 서울 침수흔적도 참고 자료

서울 공식 원천에는 2025, 2024, 2023, 2022 및 과거 연도 자료가 등록되어 있다. 현재 저장소에는 비교용으로 2022~2025 ZIP을 보관하고, API에는 2022년 19,881개 피처를 연결했다. 서울 자료를 대표 사건으로 해석하거나 최신 연도로 고정하지 않는다.

출처: [서울시 침수흔적도](https://data.seoul.go.kr/dataList/OA-15636/F/1/datasetView.do)

## 전국 자료 정책

재난안전데이터공유플랫폼의 침수흔적도 데이터셋 계열은 전국 후보 출처다. 다만 하나의 비인증 ZIP에 모든 지자체·모든 연도가 포함된다고 가정하지 않는다. 오송 자료는 API 또는 포털 record에서 사건 연도와 공간 범위를 확인한 뒤 별도 원본으로 저장한다.

수위 자료는 [한강홍수통제소 10분 수위자료](https://www.safetydata.go.kr/disaster-data/view?dataSn=7)의 `DSSP-IF-00007`을 연결 대상으로 사용한다. 서비스 키가 없으면 실제 응답을 확보한 것으로 표시하지 않는다.

전체 출처·해시·취득일은 `data/manifests/source-availability.yml`에 기록한다.

## DEM 파생 레이어 지침

DEM은 침수흔적도를 대체하지 않는다. 침수흔적도 확보 전에는 저지대·고도 설명용 `Terrain Context`만 만들 수 있으며, 노출 인구·침수 건물 수·침수 도로 길이를 계산하지 않는다.

오송 기준 구현은 Copernicus DEM GLO-30 원본에서 AOI bbox를 잘라 고도 분위값을 계산하고, AOI p25 이하 셀을 `LOW_ELEVATION_CONTEXT`로 표시한다. 이 값은 “낮은 지형” 설명 기준일 뿐이며 관측 침수면이나 수리모델 결과가 아니다.

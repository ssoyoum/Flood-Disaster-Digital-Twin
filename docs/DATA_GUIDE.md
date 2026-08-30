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

## 오송 2023 확보 자료

사건 공간 범위는 오송·궁평2지하차도·미호강 주변을 포함하는 `[36.58, 127.27, 36.68, 127.40]`이다.

| 데이터 | 데이터 연도/기준 | 저장 파일 | 상태 |
| --- | --- | --- | --- |
| DEM | 정적 자료, TanDEM-X 취득 기간 2011-2015; N36/E127 객체 수정일 2022-05-09 | `data/raw/copernicus_dem_glo30/Copernicus_DSM_COG_10_N36_00_E127_00_DEM.tif` | 확보 |
| 인구 | 2023, WorldPop Korea 100m R2025A v1 | `data/raw/worldpop/kor_pop_2023_CN_100m_R2025A_v1.tif` | 확보 |
| 건물·도로·시설·하천 | OSM 조회 스냅샷 2026-08-30 | `data/raw/osong/osm_context_2026-08-30.json` | 확보 |
| 침수흔적도 | 2023 오송 사건 record | 재난안전데이터공유플랫폼 API/다운로드 예정 | 미확보 |
| 강우·수위 | 2023-07-15 사건 시간창 | 재난안전데이터공유플랫폼·수문 관측 API 예정 | 서비스 키 대기 |

## 서울 침수흔적도 참고 자료

서울 공식 원천에는 2025, 2024, 2023, 2022 및 과거 연도 자료가 등록되어 있다. 현재 저장소에는 비교용으로 2022~2025 ZIP을 보관하고, API에는 2022년 19,881개 피처를 연결했다. 서울 자료를 대표 사건으로 해석하거나 최신 연도로 고정하지 않는다.

출처: [서울시 침수흔적도](https://data.seoul.go.kr/dataList/OA-15636/F/1/datasetView.do)

## 전국 자료 정책

재난안전데이터공유플랫폼의 침수흔적도 데이터셋 계열은 전국 후보 출처다. 다만 하나의 비인증 ZIP에 모든 지자체·모든 연도가 포함된다고 가정하지 않는다. 오송 자료는 API 또는 포털 record에서 사건 연도와 공간 범위를 확인한 뒤 별도 원본으로 저장한다.

수위 자료는 [한강홍수통제소 10분 수위자료](https://www.safetydata.go.kr/disaster-data/view?dataSn=7)의 `DSSP-IF-00007`을 연결 대상으로 사용한다. 서비스 키가 없으면 실제 응답을 확보한 것으로 표시하지 않는다.

전체 출처·해시·취득일은 `data/manifests/source-availability.yml`에 기록한다.

# FloodOps Decisions

중요한 기술·데이터 선택을 기록한다. 새로운 결정은 날짜, 결정 내용, 이유, 영향과 함께 추가한다.

## Decision Record Template

기술 선택은 다음 질문을 검토한 뒤 기록한다.

- 왜 Leaflet이 아니라 MapLibre인가?
- 왜 React Query와 Zustand를 분리했는가?
- 왜 PostGIS를 사용하는가?
- 왜 GeoJSON에서 Vector Tile로 전환하는가?
- 왜 WebSocket을 사용하는가?
- 왜 Simulation을 Backend로 분리하는가?
- 왜 Cesium은 후순위인가?

## D-001 대표 사건

- 날짜: 2026-08-30
- 결정: MVP 대표 사건은 `osong-2023`으로 시작한다.
- 이유: 하천 범람과 지하차도·교통시설 노출을 하나의 사건 흐름으로 설명할 수 있다.
- 영향: 현재 데이터 확보와 검증은 오송 2023을 우선한다.

## D-002 시간 정합성

- 날짜: 2026-08-30
- 결정: `event_year`, `data_year`, `boundary_snapshot`, `snapshot_date`를 별도 필드로 기록한다.
- 이유: 사건 발생연도와 데이터 제작·조회 시점을 혼동하지 않기 위해서다.
- 영향: 공간자료와 관측자료는 사건 시점과 가장 가까운 유효 snapshot을 선택한다.

## D-003 공식자료와 공간 기반자료의 역할 분리

- 날짜: 2026-08-30
- 결정: 침수·강우·피해·대피 해석은 공식자료를 우선하고, 건물·도로·하천·인구분포·고도 등 공간분석 기반자료는 오픈데이터를 활용할 수 있다.
- 이유: 사건 자체의 사실성은 공식자료로 확보하고, 공간분석의 재현성과 범용성은 공개 기반자료로 보완하기 위해서다.
- 영향: OSM, WorldPop, Copernicus DEM은 공식 사건자료의 대체물이 아니다.

## D-004 인구자료 우선순위

- 날짜: 2026-08-30
- 결정: 공식 세부 공간인구, 공식 읍면동 인구와 WorldPop 보정, WorldPop 단독 fallback 순서로 사용한다.
- 이유: 읍면동 전체 인구와 지역 비교는 공식 통계를 사용해야 한다.
- 영향: WorldPop은 Flood Extent 내부 공간분포 추정에만 사용한다.

## D-005 NASA POWER 분류

- 날짜: 2026-08-30
- 결정: NASA POWER 원본은 `source_type: REANALYSIS` 및 `raw_status: VERIFIED`로 기록하고, 프로젝트용 CSV 변환본만 `processed_status: DERIVED`로 기록한다.
- 이유: 원본 재분석자료와 프로젝트가 생성한 가공본을 구분하기 위해서다.
- 영향: 기상청 AWS/ASOS 실제 관측값을 주 강우자료로 유지한다.

## D-006 과거자료 기반 실행

- 날짜: 2026-08-30
- 결정: 승인된 API 응답과 다운로드 원본은 historical snapshot으로 저장하고, 애플리케이션 실행 중 매번 외부 API를 호출하지 않는다.
- 이유: 과거 사건 시뮬레이션의 재현성을 보장하기 위해서다.
- 영향: API는 초기 확보와 추후 연간 갱신에만 사용한다.

## D-007 궁평2지하차도 MVP 범위

- 날짜: 2026-08-30
- 결정: 오송 MVP의 핵심 교통시설은 궁평2지하차도 1개로 제한한다.
- 이유: 시설정보와 geometry를 검증 가능한 범위로 먼저 결합하기 위해서다.
- 영향: 차량별 노출, 실시간 교통량, 복잡한 교통 시뮬레이션은 후속 범위다.

## D-008 문서와 상태의 기준 위치

- 프로젝트 계획과 범위: `docs/PROJECT_PLAN.md`
- 개발·테스트 규칙: `docs/DEVELOPMENT_GUIDE.md`
- 데이터 정책과 상태 정의: `docs/DATA_GUIDE.md` 및 `data/manifests/`
- 실행 구조: `docs/ARCHITECTURE.md`
- 현재 작업: `TODO.md`

## Change Log

### 2026-08-30

- 기획안·개발지침·데이터 가이드를 역할별 문서로 분리했다.
- NASA POWER raw/processed 상태 정의를 분리했다.
- DSSP 피해·구호·긴급재난문자 우선순위를 낮췄다.
- `MANUAL_DOWNLOAD_REQUIRED`를 사용자 수동 다운로드 대기 상태로 정의했다.

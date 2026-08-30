# FloodOps 개발 지침

> FloodOps 기획안을 실제 개발 프로젝트로 전환하기 위한 구현 원칙, 기술 규칙, 데이터 전략, 개발 순서 및 완료 조건을 정의한다.

## 목차

- [0. 개발 원칙](#0-개발-원칙)
- [1. 개발 단계](#1-개발-단계)
- [2. 프론트엔드 아키텍처](#2-프론트엔드-아키텍처)
- [3. 기능 구조](#3-기능-구조)
- [4. 공통 컴포넌트](#4-공통-컴포넌트)
- [5. TypeScript](#5-typescript)
- [6. 데이터 분류 타입](#6-데이터-분류-타입)
- [7. 서버 상태와 UI 상태](#7-서버-상태와-ui-상태)
- [8. API 기본 구조](#8-api-기본-구조)
- [9. API 규칙](#9-api-규칙)
- [10. 비동기 UI](#10-비동기-ui)
- [11. 백엔드 아키텍처](#11-백엔드-아키텍처)
- [12. 데이터베이스](#12-데이터베이스)
- [13. PostGIS](#13-postgis)
- [14. CRS 정책](#14-crs-정책)
- [15. 데이터셋 메타데이터](#15-데이터셋-메타데이터)
- [16. 데이터 파이프라인](#16-데이터-파이프라인)
- [17. 데이터셋 매니페스트](#17-데이터셋-매니페스트)
- [18. GIS 처리](#18-gis-처리)
- [19. 홍수 노출 분석](#19-홍수-노출-분석)
- [20. 시나리오 도메인 모델](#20-시나리오-도메인-모델)
- [21. 개입 모델](#21-개입-모델)
- [22. 시뮬레이션 수준](#22-시뮬레이션-수준)
- [23. 시뮬레이션 명명 규칙](#23-시뮬레이션-명명-규칙)
- [24. 시뮬레이션 재현성](#24-시뮬레이션-재현성)
- [25. 리플레이 엔진](#25-리플레이-엔진)
- [26. 리플레이 규칙](#26-리플레이-규칙)
- [27. 시뮬레이션 비동기 확장](#27-시뮬레이션-비동기-확장)
- [28. 2D GIS](#28-2d-gis)
- [29. 3D Digital Twin](#29-3d-digital-twin)
- [30. 성능](#30-성능)
- [31. 대용량 공간데이터 전략](#31-대용량-공간데이터-전략)
- [32. 프론트엔드 테스트](#32-프론트엔드-테스트)
- [33. 백엔드 테스트](#33-백엔드-테스트)
- [34. 공간 테스트](#34-공간-테스트)
- [35. E2E 테스트](#35-e2e-테스트)
- [36. 데이터베이스 마이그레이션](#36-데이터베이스-마이그레이션)
- [37. 로깅](#37-로깅)
- [38. 헬스 체크](#38-헬스-체크)
- [39. Docker](#39-docker)
- [40. 배포](#40-배포)
- [41. CI/CD](#41-cicd)
- [42. README](#42-readme)
- [43. 기술 의사결정 기록](#43-기술-의사결정-기록)
- [44. 개발 순서](#44-개발-순서)
- [45. MVP 완료 조건](#45-mvp-완료-조건)
- [46. Portfolio V1 완료 조건](#46-portfolio-v1-완료-조건)
- [47. Advanced 완료 조건](#47-advanced-완료-조건)
- [48. 데이터 확보 체크리스트](#48-데이터-확보-체크리스트)
- [49. 데이터 탈락 기준](#49-데이터-탈락-기준)
- [50. 프로젝트 최종 개발 원칙](#50-프로젝트-최종-개발-원칙)

## 0. 개발 원칙

- 데이터 확보 가능성을 기능 구현보다 먼저 검증한다.
- 1개 사건으로 End-to-End Vertical Slice를 완성한 후 확장한다.
- Frontend, Backend, GIS Processing, Simulation을 분리한다.
- 실제 관측값, 내부 계산값, Simulation 값을 데이터 모델에서 구분한다.
- 3D보다 2D와 핵심 의사결정 기능을 먼저 완성한다.
- 사건 수보다 완성도, 테스트, 배포, 재현성을 우선한다.
- 모든 주요 기술 선택은 README에서 선택 이유를 설명할 수 있어야 한다.
- 기능 구현뿐 아니라 성능, 정확성, 한계도 측정한다.

## 1. 개발 단계

### Phase 1 — MVP

- 국내 홍수 사건 1개
- React + TypeScript
- MapLibre
- FastAPI
- PostGIS
- Flood Extent
- Spatial Exposure Analysis
- Baseline Scenario
- Intervention
- Before / After Comparison
- Test
- Deploy

### Phase 2 — Portfolio V1

- 해외 사건 1개 추가: 2026 네팔 빙하
- Historical Replay
- WebSocket
- Scenario 저장
- 대용량 공간데이터 최적화
- Playwright E2E
- Performance Benchmark
- Architecture Documentation

### Phase 3 — Advanced

- Cesium 3D
- Evacuation Analysis
- 외부 Hydraulic Model 연동
- AI Situation Brief
- 3개 이상 사건
- Job-based Simulation
- 최대 5개 사건 확장

## 2. 프론트엔드 아키텍처

~~~text
src/
├── app/
├── components/
├── features/
├── pages/
├── hooks/
├── services/
├── stores/
├── types/
└── utils/
~~~

- pages는 화면 조합 역할만 담당한다.
- 기능별 UI와 로직은 features 내부로 분리한다.
- API 호출은 services에서 관리한다.
- 공통 UI와 GIS 컴포넌트를 분리한다.
- 페이지 컴포넌트에서 직접 복잡한 GIS 처리나 API 호출을 하지 않는다.

## 3. 기능 구조

~~~text
features/
├── events/
├── map/
├── monitoring/
├── replay/
├── scenarios/
├── simulation/
├── intervention/
├── comparison/
└── infrastructure/
~~~

예시:

~~~text
features/scenarios/
├── components/
├── hooks/
├── services/
├── stores/
├── types/
└── utils/
~~~

기능 간 의존성을 최소화한다.

## 4. 공통 컴포넌트

~~~text
components/
├── map/
├── dashboard/
├── monitoring/
├── simulation/
├── intervention/
├── charts/
├── layout/
└── common/
~~~

하나의 컴포넌트가 다음 역할을 모두 담당하지 않도록 한다.

- API 호출
- 전역 상태 관리
- GIS 계산
- UI 렌더링
- Simulation 계산

## 5. TypeScript

- any 사용을 최소화한다.
- API Request / Response 타입을 정의한다.
- 도메인 타입을 명확하게 정의한다.

핵심 도메인 타입 예시:

~~~text
FloodEvent
RiverGauge
RainGauge
Observation
FloodExtent
Infrastructure
Shelter
Scenario
Intervention
SimulationRun
SimulationResult
ComparisonResult
DatasetMetadata
~~~

## 6. 데이터 분류 타입

데이터 유형을 명시적으로 정의한다.

~~~ts
type DataOrigin =
  | "OBSERVED"
  | "DERIVED"
  | "SIMULATED";
~~~

모든 핵심 분석 데이터는 DataOrigin을 포함한다.

## 7. 서버 상태와 UI 상태

### TanStack Query

서버에서 가져오는 데이터에 사용한다.

- events
- gauges
- observations
- flood extents
- infrastructure
- scenarios
- simulation results
- comparison results

### Zustand

클라이언트 UI 상태에 사용한다.

- selectedEventId
- currentTime
- replaySpeed
- mapMode
- selectedLayers
- selectedInfrastructure
- selectedScenarioId
- simulationMode
- comparisonMode

## 8. API 기본 구조

~~~http
GET /api/events
GET /api/events/{eventId}
GET /api/events/{eventId}/flood
GET /api/events/{eventId}/flood/timeline
GET /api/events/{eventId}/infrastructure
GET /api/gauges
GET /api/gauges/{gaugeId}
GET /api/gauges/{gaugeId}/observations
GET /api/infrastructure
GET /api/shelters
GET /api/scenarios
GET /api/scenarios/{scenarioId}
POST /api/scenarios
POST /api/scenarios/{scenarioId}/runs
POST /api/scenarios/{scenarioId}/interventions
GET /api/scenarios/{baselineId}/compare/{scenarioId}
GET /api/simulations/{simulationId}
GET /health
~~~

## 9. API 규칙

- Pydantic Schema로 Request와 Response를 검증한다.
- 오류 응답 형식을 통일한다.
- Swagger / OpenAPI를 API 계약 확인에 활용한다.
- HTTP Status Code를 의미에 맞게 사용한다.

오류 응답 예시:

~~~json
{
  "error": {
    "code": "INVALID_SCENARIO",
    "message": "Scenario parameters are invalid.",
    "details": {}
  }
}
~~~

## 10. 비동기 UI

Frontend는 모든 서버 데이터에 대해 다음 상태를 처리한다.

- loading
- success
- error
- empty
- retry

Simulation 실행 중에는 Processing 상태를 명시한다. 긴 작업은 API 요청과 결과 조회를 분리할 수 있도록 설계한다.

## 11. 백엔드 아키텍처

~~~text
backend/
├── api/
├── schemas/
├── models/
├── services/
├── repositories/
├── simulation/
├── gis/
├── replay/
├── database/
├── logging/
└── tests/
~~~

기본 흐름:

~~~text
API
→ Service
→ Repository
→ Database
~~~

Business Logic은 API Route에 직접 작성하지 않는다.

## 12. 데이터베이스

핵심 테이블:

~~~text
flood_events
river_gauges
rain_gauges
gauge_observations
flood_extents
buildings
roads
infrastructure
shelters
population_grids
scenarios
interventions
simulation_runs
simulation_results
dataset_metadata
~~~

## 13. PostGIS

- Geometry 타입을 사용한다.
- 다음 주요 공간 질의를 구현한다.

~~~text
Flood Extent × Building
Flood Extent × Road
Flood Extent × Infrastructure
Flood Extent × Population
Shelter × Population
Road Closure × Evacuation Route
~~~

- 공간 Index를 생성한다.
- GiST Index를 기본으로 검토한다.

## 14. CRS 정책

- Raw Dataset의 CRS를 기록한다.
- 분석용 CRS와 Web Display CRS를 구분한다.
- 웹 표현은 WGS84 / Web Mercator를 사용한다.
- 면적·거리 계산은 적절한 Projected CRS에서 수행한다.
- CRS 변환 위치와 이유를 문서화한다.

## 15. 데이터셋 메타데이터

모든 핵심 Dataset에 다음 Metadata를 관리한다.

~~~text
source
source_url
license
acquired_at
event_year
boundary_snapshot
data_year
crs
unit
spatial_resolution
temporal_resolution
quality_flag
processing_method
dataset_version
checksum
~~~

`event_year`는 분석 대상 재난 사건의 발생연도이고, `boundary_snapshot`은 공간 집계에 사용한 행정경계의 기준연도·버전이다. 두 값은 사건연도와 경계 자료연도가 다를 수 있으므로 반드시 별도 필드로 저장한다. 행정경계는 가능한 경우 사건연도, 그렇지 않으면 가장 가까운 한국 공식 자료를 우선 사용한다. 이 규칙은 후속 사건에도 동일하게 적용한다.

인구 데이터는 다음 순서로 선택한다.

1. 통계청·SGIS 등 한국 공식 세부 공간인구
2. 공식 읍면동 전체 인구와 WorldPop 공간분포 보정
3. WorldPop 단독 추정은 공식 자료 확보가 어려운 경우의 fallback

읍면동 전체 인구와 지역 간 비교값은 공식 통계만 사용한다. WorldPop은 Flood Extent 내부 노출 인구의 공간분포 추정에만 사용하며, 공식 총인구를 대체하지 않는다.

## 16. 데이터 파이프라인

Raw Data를 직접 수정하지 않는다.

~~~text
data/
├── raw/
├── interim/
├── processed/
└── manifests/
~~~

처리 흐름:

~~~text
Raw Raster / Vector
→ Validation
→ CRS 변환
→ Geometry Repair
→ Attribute Normalization
→ Common Schema
→ Spatial Processing
→ PostGIS Load
~~~

## 17. 데이터셋 매니페스트

각 Dataset마다 Manifest를 관리한다.

~~~text
dataset_name
source
download_date
license
checksum
original_crs
output_crs
processing_script
output_file
version
~~~

동일 Pipeline을 다시 실행하면 processed dataset을 재생성할 수 있어야 한다.

## 18. GIS 처리

다음 도구를 사용한다.

- GeoPandas
- Rasterio
- Shapely
- PyProj

핵심 처리:

- CRS 변환
- Geometry Validation
- Spatial Join
- Intersection
- Buffer
- Clip
- Raster Sampling
- Zonal Statistics
- DEM Processing
- Flood Exposure Calculation

## 19. 홍수 노출 분석

Flood Extent와 공간데이터를 교차하여 다음 지표를 계산한다.

- Flooded Area
- Exposed Buildings
- Affected Road Length
- Affected Infrastructure
- Exposed Population
- Affected Shelter
- Critical Facility Risk

결과는 Derived Data로 저장한다.

## 20. 시나리오 도메인 모델

Scenario는 다음 구조를 가진다.

~~~text
Scenario
├── Flood Event
├── Initial Conditions
├── Model Version
├── Intervention[]
└── Simulation Run[]
~~~

- Baseline Scenario는 Intervention이 없는 Scenario다.
- Comparison은 동일한 Event와 기준 조건을 공유하는 Scenario끼리 수행한다.

## 21. 개입 모델

Intervention Type:

~~~text
EVACUATION
ROAD_CLOSURE
SHELTER_OPEN
TEMPORARY_BARRIER
LEVEE_IMPROVEMENT
INFRASTRUCTURE_PROTECTION
~~~

Intervention에는 다음 정보를 저장한다.

~~~text
type
geometry
start_time
parameters
estimated_cost
description
~~~

## 22. 시뮬레이션 수준

### Level 1

Water Level / Elevation 기반 Flood Scenario

### Level 2

~~~text
Flood Extent
× Buildings
× Roads
× Infrastructure
× Population
~~~

### Level 3

~~~text
Flood Arrival Time
× Evacuation Time
× Shelter Capacity
~~~

### Level 4

외부 Hydraulic Model Result Integration

- HEC-RAS
- LISFLOOD-FP 등

## 23. 시뮬레이션 명명 규칙

내부 단순 모델은 다음과 같이 표현한다.

- What-if Flood Scenario
- Simplified Inundation Scenario
- Scenario Estimate

검증되지 않은 내부 모델을 Hydrodynamic Simulation이라고 표현하지 않는다. 공식 또는 외부 수리모형 결과는 별도 분류한다.

## 24. 시뮬레이션 재현성

Scenario 실행 시 다음 정보를 기록한다.

~~~text
model_name
model_version
input_parameters
input_dataset_version
input_hash
created_at
execution_time
assumptions
limitations
~~~

동일 입력과 동일 모델 버전으로 동일한 결과를 생성할 수 있어야 한다.

## 25. 리플레이 엔진

Historical Observation을 시간축으로 재생한다.

- REST API는 초기 데이터 로딩과 전체 조회에 사용한다.
- WebSocket은 시간 순 Observation 전달에 사용한다.

Endpoint:

~~~http
WS /ws/events/{eventId}/replay
~~~

메시지 예시 필드:

~~~text
event_id
timestamp
observation_type
station_id
value
unit
quality_flag
origin
~~~

## 26. 리플레이 규칙

- PLAY / PAUSE / SPEED 변경은 데이터의 원본 timestamp를 변경하지 않는다.
- Frontend는 표현 시간만 조절한다.
- Replay 시작 시 현재 Event와 기준 시점을 명확하게 표시한다.
- Historical Replay Badge를 항상 표시한다.

## 27. 시뮬레이션 비동기 확장

- 초기 Simulation은 동기 요청이 가능하다.
- 처리시간이 길어질 경우 Job 기반으로 전환한다.

요청:

~~~http
POST /api/scenarios/{scenarioId}/runs
~~~

응답:

~~~text
simulation_id
status
status_url
~~~

결과 조회:

~~~http
GET /api/simulations/{simulationId}
~~~

상태:

~~~text
QUEUED
RUNNING
COMPLETED
FAILED
~~~

## 28. 2D GIS

- MapLibre를 기본 지도 엔진으로 사용한다.
- MVP는 GeoJSON 사용이 가능하다.
- 데이터 증가 시 다음으로 확장한다.

~~~text
MVT
PMTiles
COG
Tile-based Raster
~~~

화면에 필요한 영역과 Zoom Level의 데이터만 로딩한다.

## 29. 3D Digital Twin

Cesium을 사용한다.

표현 대상:

- Terrain
- Buildings
- River
- Flood
- Infrastructure
- Shelter
- Scenario Result

3D에서 복잡한 분석 로직을 처리하지 않는다. 3D는 Situation Awareness 중심으로 사용한다.

## 30. 성능

다음 지표를 측정한다.

- Initial Map Load Time
- Layer Toggle Response
- Timeline Update Latency
- API Response Time
- Spatial Query Time
- Simulation Execution Time
- WebSocket Replay Delay
- Feature Rendering Performance

각 주요 버전에서 Benchmark를 README에 기록한다.

## 31. 대용량 공간데이터 전략

초기:

~~~text
GeoJSON
~~~

확장:

~~~text
Vector Tile
PMTiles
COG
Backend Bounding Box Query
LOD
Clustering
Generalization
~~~

Frontend에 전체 원본 Dataset을 무조건 전달하지 않는다.

## 32. 프론트엔드 테스트

도구:

- Vitest
- React Testing Library

테스트 대상:

- UI Component
- Custom Hook
- Zustand Store
- TanStack Query State
- Loading
- Error
- Empty
- Scenario Form Validation
- Comparison UI

## 33. 백엔드 테스트

도구:

- Pytest

테스트 대상:

- API
- Service
- Repository
- Simulation Validation
- Spatial Calculation
- Data Origin Validation
- Scenario Comparison

## 34. 공간 테스트

공간 질의는 핵심 테스트 대상으로 둔다.

예시:

- Flood Polygon과 교차하는 건물 수
- 침수 도로 길이
- 시설 Intersection
- Shelter Buffer
- Population Exposure
- CRS 변환 후 거리·면적 계산

## 35. E2E 테스트

Playwright를 추가한다.

핵심 E2E Flow:

~~~text
Event 선택
→ 지도 로딩
→ Replay 실행
→ Timeline 변경 확인
→ Scenario 생성
→ Simulation 실행
→ Intervention 적용
→ Baseline Comparison
→ 결과 확인
~~~

최소 하나의 핵심 사용자 흐름은 CI에서 자동 실행한다.

## 36. 데이터베이스 마이그레이션

- Alembic을 사용한다.
- Schema 변경을 수동 SQL 수정으로 관리하지 않는다.
- Migration을 통해 새로운 환경에서도 DB Schema를 재현할 수 있어야 한다.
- Sample / Seed Dataset을 제공한다.

## 37. 로깅

Structured Logging을 사용한다.

최소 다음 정보를 기록한다.

~~~text
request_id
event_id
scenario_id
simulation_id
execution_time
error_type
~~~

Simulation 실패 시 어떤 입력과 Dataset에서 실패했는지 추적할 수 있어야 한다.

## 38. 헬스 체크

Endpoint:

~~~http
GET /health
~~~

확인 항목:

- Backend
- Database
- PostGIS
- 필요 시 External API

## 39. Docker

docker-compose.yml은 다음 서비스로 구성한다.

- frontend
- backend
- postgis

환경변수를 사용한다. .env 파일은 Git에 포함하지 않으며 .env.example을 제공한다.

## 40. 배포

필수 항목:

- CORS
- DB Migration
- Health Check
- Logging
- Environment Variables
- Build
- Test
- Docker
- Production Config

## 41. CI/CD

Pull Request 또는 Main Branch Merge 시 다음을 실행한다.

- Frontend Lint
- Frontend Test
- Frontend Build
- Backend Lint
- Backend Test
- Migration Validation
- Playwright E2E
- Docker Build

모든 핵심 테스트가 통과한 결과만 배포한다.

## 42. README

README 첫 화면에는 기술 목록보다 프로젝트 문제와 핵심 결과를 먼저 보여준다.

필수 구성:

- Project Summary
- Problem
- Solution
- Live Demo
- 30~60초 Demo GIF 또는 Video
- Architecture Diagram
- Data Pipeline Diagram
- Database ERD
- API Documentation
- Data Source Table
- Observed / Derived / Simulated 정의
- Simulation Assumptions
- Scenario Comparison Example
- Testing Strategy
- Performance Benchmark
- Technical Trade-offs
- Known Limitations
- Future Work

## 43. 기술 의사결정 기록

주요 기술 선택의 이유와 변경 기록은 [DECISIONS.md](DECISIONS.md)를 기준 문서로 관리한다.

## 44. 개발 순서

1. 국내 홍수 후보 3~5개 조사
2. 핵심 데이터 확보 여부 확인
3. MVP 사건 1개 선정
4. Raw Data 수집
5. GIS Processing Pipeline
6. Dataset Metadata / Manifest 구축
7. PostGIS Schema
8. FastAPI REST API
9. React + TypeScript
10. MapLibre 2D GIS
11. Flood Exposure Analysis
12. Baseline Scenario
13. Intervention
14. Before / After Comparison
15. Test
16. Docker
17. Deploy
18. Historical Replay
19. WebSocket
20. 해외 사건 1개 추가
21. Performance Optimization
22. Playwright
23. Cesium 3D
24. Advanced Simulation
25. AI Situation Brief
26. 최대 5개 사건 확장

## 45. MVP 완료 조건

- [ ] 국내 홍수 사건 1개가 존재한다.
- [ ] 사건을 선택할 수 있다.
- [ ] 실제 수문·공간데이터가 지도에 표시된다.
- [ ] Flood Extent와 건물·도로·시설의 공간 질의가 수행된다.
- [ ] Baseline Scenario가 존재한다.
- [ ] 최소 1개의 Intervention을 적용할 수 있다.
- [ ] Baseline과 Intervention 결과를 비교할 수 있다.
- [ ] Observed / Derived / Simulated가 UI에서 구분된다.
- [ ] REST API를 Frontend에서 실제 사용한다.
- [ ] 핵심 기능 자동화 테스트가 존재한다.
- [ ] Docker로 동일 환경을 재현할 수 있다.
- [ ] 배포된 Demo URL이 존재한다.

## 46. Portfolio V1 완료 조건

- [ ] 국내 사건 + 해외 사건 최소 2개
- [ ] Historical Replay 동작
- [ ] WebSocket 사용
- [ ] Replay PLAY / PAUSE / SPEED 동작
- [ ] Scenario 저장 및 재실행 가능
- [ ] Intervention 최소 3종
- [ ] Comparison Dashboard 존재
- [ ] 성능 Benchmark 존재
- [ ] Playwright E2E 존재
- [ ] Architecture Diagram 존재
- [ ] ERD 존재
- [ ] Data Provenance 존재
- [ ] 공개 Live Demo 존재

## 47. Advanced 완료 조건

- [ ] Cesium 3D 구현
- [ ] 3개 이상 사건
- [ ] Evacuation Analysis
- [ ] 외부 Hydraulic Model Result 연동 가능
- [ ] Job 기반 Simulation
- [ ] AI Situation Brief
- [ ] 최대 5개 사건 공통 Schema 지원

## 48. 데이터 확보 체크리스트

| 데이터 | 출처 후보 |
| --- | --- |
| DEM | Copernicus DEM GLO-30 |
| Flood Extent | 한국 행정안전부·지자체 공식 침수흔적도 우선, 보조적으로 Copernicus Emergency Management Service |
| River / Discharge | Copernicus GloFAS |
| Rainfall | 기상청 AWS/ASOS·지자체 관측망 우선, NASA POWER/GPM/IMERG는 보조·비교 |
| River / Watershed | HydroSHEDS |
| Buildings / Roads / Facilities | OpenStreetMap |
| Population | 통계청·SGIS 공식 세부 공간인구 → 공식 읍면동 인구 + WorldPop 보정 → WorldPop fallback |
| Administrative Boundaries | 사건연도 또는 가장 가까운 한국 공식 행정경계, 불가 시 기준연도를 명시한 공개 경계 |
| Satellite | Copernicus Data Space / Sentinel |
| 대한민국 데이터 | 한강홍수통제소, WAMIS, K-water, 공공데이터포털 |

### 48.1 강우자료 확보 workflow

모든 사건은 동일한 강우자료 확보 절차를 사용한다.

`event` → `location + date` → `KMA station 후보 검색` → `관측소 ID / 기간 / 요소 결정`

자동 다운로드가 공식적으로 지원되면 원본을 `data/raw/`에 저장하고 검증한다. 인증·로그인·세션·복잡한 웹 폼 자동화가 필요한 경우 `MANUAL_DOWNLOAD_REQUIRED`로 기록하고, 사용자가 공식 CSV를 지정 폴더에 넣은 뒤 동일한 검증·정규화 절차를 적용한다.

기상청 HTML/JavaScript 역분석, hidden form 재현, 세션 우회, 다운로드 URL 추측, 비공식 scraping은 사용하지 않는다. NASA POWER는 KMA 관측값을 대체하지 않는 `REANALYSIS` 보조자료이며, 프로젝트용 CSV 변환본만 `DERIVED`로 분류한다.

`MANUAL_DOWNLOAD_REQUIRED`와 데이터별 관측소·기간·요소는 `data/manifests/source-availability.yml`에서 확인하고, 작업 상태는 `TODO.md`에서 확인한다. 이 상태는 새 데이터셋 추가 수집 지시가 아니라 기존 공식 출처의 사용자 수동 다운로드 대기 상태다.

## 49. 데이터 탈락 기준

- 핵심 데이터 출처를 확인할 수 없는 사건은 제외한다.
- 공간 범위가 맞지 않는 사건은 제외한다.
- 시간 정보가 부족한 데이터는 Replay 대상에서 제외한다.
- 사건 설명용 공식자료를 OSM·NASA 등 공간분석용 보조자료로 대체하지 않는다.
- 라이선스가 불분명한 데이터는 공개 프로젝트에 사용하지 않는다.
- CRS 또는 단위를 확인할 수 없는 데이터는 분석에 사용하지 않는다.
- 해상도가 분석 목적에 부족한 경우 데이터 한계를 명시하거나 대체한다.

## 50. 프로젝트 최종 개발 원칙

- 멋있는 3D 화면보다 작동하는 의사결정 흐름을 우선한다.
- 사건 5개보다 완성된 사건 1개를 우선한다.
- AI보다 실제 데이터와 공간분석을 우선한다.
- Simulation을 실제 관측값처럼 표현하지 않는다.
- 데이터 출처와 라이선스를 숨기지 않는다.
- 결과만 보여주지 않고 계산 과정과 가정을 설명한다.
- 기능만 구현하지 않고 테스트한다.
- 테스트만 하지 않고 배포한다.
- 배포만 하지 않고 성능을 측정한다.
- 코드만 보여주지 않고 기술적 의사결정을 설명한다.

FloodOps의 핵심은 다음 한 문장으로 정의한다.

> 홍수가 어디까지 오는지를 보여주는 시스템이 아니라, 어떤 대응을 선택했을 때 피해가 얼마나 줄어드는지를 비교하는 Flood Decision Digital Twin을 만든다.

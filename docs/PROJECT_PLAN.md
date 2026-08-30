# FloodOps — Flood Disaster Decision Digital Twin 기획안

실제 홍수·수문·공간 데이터를 기반으로 재난 상황을 디지털 공간에 재현하고, **관측 → 분석 → 시뮬레이션 → 방재 개입 → 결과 비교**까지 수행하는 Web-based Flood Decision Digital Twin.

## 1. 프로젝트 정의

FloodOps는 단순히 홍수 범위를 지도에 표시하는 시스템이 아니다.

실제 수문·공간 데이터를 기반으로 홍수 상황을 재현하고, 사용자가 대피·도로통제·대피소 개방·임시 방어시설 등의 방재 조치를 적용한 뒤 Baseline과 Intervention Scenario의 피해 차이를 정량적으로 비교하는 의사결정 지원 플랫폼이다.

핵심 질문은 다음과 같다.

- 현재 홍수로 어떤 지역과 시설이 영향을 받는가?
- 홍수는 언제 특정 지역에 도달하는가?
- 현재 도로와 대피소 상태에서 주민 대피가 가능한가?
- 특정 도로를 통제하면 대피시간이 어떻게 달라지는가?
- 대피소를 추가 개방하면 위험 인구가 얼마나 줄어드는가?
- 임시 방어시설을 설치하면 침수 피해가 얼마나 감소하는가?
- 여러 방재 대안을 비교했을 때 어떤 대안이 가장 효과적인가?

## 2. 프로젝트 목표

- React와 TypeScript 기반 웹개발 역량을 프로젝트의 핵심으로 한다.
- GIS와 공간데이터를 활용하여 재난 상황을 분석하고 시각화한다.
- Historical Observation을 Replay하여 실시간 재난 관제 구조를 구현한다.
- 홍수 Scenario와 방재 Intervention의 효과를 동일한 지표로 비교한다.
- PostGIS를 이용해 홍수범위 × 건물 × 도로 × 시설의 공간분석을 수행한다.
- 2D GIS와 3D Digital Twin의 역할을 명확히 구분한다.
- 실제 관측 데이터와 프로젝트 내부에서 계산한 결과를 명확하게 구분한다.
- 수자원은 전문 도메인으로 활용하지만 시스템 구조는 다른 재난·공간정보 서비스에도 확장할 수 있도록 설계한다.

## 3. 핵심 사용자

### Primary User

- 지자체 재난안전 담당자
- 수자원·환경 관련 공공기관 실무자
- 재난·방재 엔지니어링 실무자
- GIS·공간정보 담당자

### Secondary User

- 스마트시티 운영기관
- 디지털트윈 구축기업
- 연구기관
- 재난 대응 교육 및 훈련기관

## 4. 핵심 사용자 흐름

```text
홍수 사건 선택
→ 2D GIS 공간 확인
→ Historical Replay 실행
→ 강우·수위·유량 관제
→ 위험지역 및 영향시설 분석
→ Baseline Scenario 확인
→ 방재 Intervention 선택
→ Scenario 재실행
→ Before / After 결과 비교
→ 상황보고서 및 의사결정 지표 확인
```

## 5. 핵심 기능

### 5.1 Event Management

홍수 사건을 공통 데이터 모델로 관리한다.

- 초기 MVP에서는 국내 홍수 사건 1개를 완성한다.
- Portfolio V1에서는 국내 홍수 사건 1개와 해외 대표 사건 1개를 구현한다.
- 최종 확장 단계에서 최대 5개 사건까지 동일한 Schema로 관리한다.

### 5.2 2D GIS

MapLibre 기반으로 다음 레이어를 표현한다.

- DEM 기반 지형정보
- 하천
- 유역
- 홍수범위
- 수위관측소
- 강우관측소
- 건물
- 도로
- 주요 기반시설
- 대피소
- 인구 또는 인구격자
- 위험지역

2D GIS는 공간검색·시설검색·영향분석·레이어 비교에 집중한다.

### 5.3 Historical Replay

과거 실제 수문 데이터를 시간축으로 재생한다.

```text
Historical Observation
→ Replay Engine
→ WebSocket
→ React Monitoring UI
```

사용자는 다음 기능을 사용할 수 있다.

- PLAY
- PAUSE
- 1×
- 2×
- 5×
- 10×
- Timeline 이동

실제 실시간 센서가 아닌 경우 UI와 README에 Historical Replay임을 명확하게 표시한다.

### 5.4 Real-time Monitoring

Replay 또는 향후 실제 API를 통해 다음 데이터를 관제한다.

- Rainfall
- Water Level
- Discharge
- Dam Inflow
- Dam Release
- Flood Warning
- Infrastructure Status

지도와 차트는 동일한 시간 상태를 공유한다.

### 5.5 Flood Scenario Engine

초기 버전은 물리적으로 검증된 수리모형인 것처럼 표현하지 않는다.

초기 기능 명칭은 다음과 같이 한다.

**What-if Flood Scenario Engine**

| 수준 | 내용 |
| --- | --- |
| Level 1 | Water Level / Elevation 기반 단순 침수 시나리오 |
| Level 2 | Flood Extent × Buildings × Roads × Population × Infrastructure |
| Level 3 | Flood Arrival Time × Evacuation Time |
| Level 4 | 필요할 경우 HEC-RAS, LISFLOOD-FP 등 외부 수리모형 결과 연동 |

외부 수리모형 결과를 사용하는 경우 내부 Scenario Engine과 별도 데이터 유형으로 구분한다.

## 6. Disaster Intervention

다음과 같은 방재 개입을 Scenario에 적용할 수 있다.

- **Evacuation** — 특정 지역 주민 선제 대피
- **Road Closure** — 침수 예상 도로 선제 통제
- **Shelter Opening** — 추가 대피소 개방
- **Temporary Barrier** — 임시 방어시설 또는 이동식 차수벽 설치
- **Levee / River Improvement** — 제방 또는 하천개선 효과 Scenario
- **Infrastructure Protection** — 중요시설 우선 보호 Scenario

Intervention은 독립 기능이 아니라 Scenario의 일부로 관리한다.

## 7. Scenario Comparison

Baseline과 Intervention Scenario를 동일한 조건과 지표로 비교한다.

핵심 비교 지표는 다음과 같다.

- Flooded Area
- Exposed Population
- Exposed Buildings
- Affected Road Length
- Critical Infrastructure at Risk
- Population Requiring Evacuation
- Unreachable Shelter Population
- Flood Arrival Time
- Evacuation Clearance Time
- Avoided Exposure
- Avoided Building Impact
- Avoided Road Disruption
- Intervention Cost
- Benefit / Cost Ratio

공식 피해액 산정모델을 사용하지 않는 경우 비용 결과는 **Estimated Scenario Value**임을 명확하게 표시한다.

## 8. 핵심 제품 화면

FloodOps의 대표 화면은 단순한 3D 홍수 애니메이션이 아니다.

### Baseline

| 지표 | 값 |
| --- | ---: |
| 위험인구 | 4,210명 |
| 침수 예상 건물 | 327동 |
| 통행불가 도로 | 8.4km |
| 고립 예상 인구 | 820명 |
| 대피 완료 예상시간 | 84분 |

사용자가 다음 Intervention을 선택한다.

- Shelter A 추가 개방
- Road B 선제 통제
- Temporary Barrier C 설치

### Intervention Result

| 지표 | Baseline | Intervention |
| --- | ---: | ---: |
| 위험인구 | 4,210명 | 2,730명 |
| 고립 예상 인구 | 820명 | 190명 |
| 대피 완료시간 | 84분 | 52분 |
| 예상 노출인구 감소 | — | 35.2% |

이 Before / After 화면을 프로젝트의 대표 기능으로 삼는다.

## 9. 3D Digital Twin

Cesium 기반으로 다음 데이터를 표현한다.

- Terrain
- Buildings
- River
- Flood Extent
- Critical Infrastructure
- Shelter
- Evacuation Zone

역할은 다음과 같이 구분한다.

| 영역 | 역할 |
| --- | --- |
| 2D GIS | 분석·검색·공간질의·레이어 비교 |
| 3D Digital Twin | 상황인지·지형 이해·재난 관제·프레젠테이션 |

3D 기능은 2D GIS와 핵심 Scenario 기능이 완성된 뒤 구현한다.

## 10. 데이터 전략

데이터 확보 가능성을 기능 개발보다 먼저 검증한다.

사건을 선정할 때 다음 데이터를 우선 확인한다.

- DEM
- Flood Extent
- River / Watershed
- Rainfall
- Water Level
- Discharge
- Buildings
- Roads
- Infrastructure
- Shelters
- Population

데이터가 충분하지 않은 사건은 프로젝트 대상에서 제외한다.

## 11. 사건 구성 전략

| 단계 | 범위 |
| --- | --- |
| MVP | 대한민국 홍수 사건 1개 |
| Portfolio V1 | 대한민국 홍수 사건 1개 + 해외 대표 홍수 사건 1개 |
| Advanced | 3개 이상 사건 |
| Stretch Goal | 최대 5개 사건 |

사건 수보다 End-to-End 완성도와 시스템 재현성을 우선한다.

## 12. 데이터 출처

| 데이터 | 출처 |
| --- | --- |
| DEM | Copernicus DEM GLO-30 |
| Flood Extent | Copernicus Emergency Management Service |
| River / Discharge | Copernicus GloFAS |
| Rainfall | NASA GPM / IMERG |
| River / Watershed | HydroSHEDS |
| Buildings / Roads / Facilities | OpenStreetMap, 국가별 공공 공간정보 |
| Population | 통계청·SGIS 공식 세부 공간인구 우선, 공식 읍면동 인구 + WorldPop 보정, WorldPop fallback |
| Satellite | Copernicus Data Space, Sentinel |
| 대한민국 수문자료 | 한강홍수통제소, WAMIS, K-water, 공공데이터포털 |

인구 전체값과 지역별 비교는 공식 읍면동 통계를 사용한다. WorldPop은 Flood Extent 내부 공간분포 추정에만 사용하며, 공식 세부격자가 없을 때 공식 읍면동 인구를 공간적으로 보정하는 용도로 우선 적용한다.

행정경계는 분석 사건의 `event_year`와 별도로 `boundary_snapshot`을 관리한다. 가능한 경우 사건연도 또는 가장 가까운 한국 공식 행정경계를 선택하며, 다른 연도의 시나리오에도 동일한 기준을 적용한다.

## 13. 데이터 신뢰성 분류

모든 데이터는 다음 세 가지 유형으로 구분한다.

| 유형 | 정의 |
| --- | --- |
| `OBSERVED` | 공식 기관이나 실제 관측 시스템에서 취득한 값 |
| `DERIVED` | 실제 데이터와 공간분석을 기반으로 프로젝트 내부에서 계산한 값 |
| `SIMULATED` | Scenario Engine을 통해 생성된 가정 결과 |

UI에서는 Badge와 Legend를 이용해 세 유형을 명확하게 구분한다.

## 14. 데이터 Provenance

가능한 모든 데이터에 다음 정보를 관리한다.

- `source`
- `source_url`
- `license`
- `acquired_at`
- `CRS`
- `unit`
- `spatial_resolution`
- `temporal_resolution`
- `quality_flag`
- `confidence`
- `processing_method`
- `dataset_version`

공공 데이터와 프로젝트 내부 계산 결과의 출처를 역추적할 수 있도록 한다.

## 15. Simulation 재현성

모든 Simulation은 동일한 데이터와 입력으로 다시 실행할 수 있어야 한다.

Scenario에는 다음 정보를 저장한다.

- `model_name`
- `model_version`
- `input_parameters`
- `input_dataset_version`
- `input_hash`
- `assumptions`
- `limitations`
- `created_at`

결과만 DB에 저장하는 것이 아니라 어떤 입력과 모델에서 생성된 결과인지 추적한다.

## 16. Analysis Dashboard

Dashboard는 단순 통계표보다 의사결정 지표를 중심으로 구성한다.

### Monitoring

- Current Rainfall
- Current Water Level
- Current Discharge
- Flood Warning Level

### Exposure

- Exposed Population
- Exposed Buildings
- Affected Road Length
- Critical Infrastructure

### Evacuation

- Evacuation Required
- Reachable Shelter Capacity
- Unreachable Population
- Estimated Clearance Time

### Scenario

- Baseline Risk
- Intervention Risk
- Risk Reduction
- Estimated Intervention Cost
- Benefit / Cost

## 17. AI Situation Brief — Optional

AI는 핵심 Simulation Engine이 아니라 보조 기능으로 사용한다.

AI가 새로운 위험도를 임의 생성하지 않는다. 이미 시스템에서 계산된 다음 정보만 입력으로 사용한다.

- 현재 강우
- 수위
- 유량
- 위험시설
- 침수예상지역
- 대피 필요 인구
- 통제도로
- 대피소
- Intervention 결과

예시:

> 현재 Baseline Scenario에서는 A지역 주민 820명이 대피소 접근이 제한된다. Shelter B를 추가 개방할 경우 고립 예상 인구가 190명으로 감소한다.

AI 결과에는 Scenario와 Data Source를 연결한다.

## 18. 기술 방향

| 영역 | 기술 |
| --- | --- |
| Frontend | React, TypeScript, Vite, MapLibre, Cesium, Zustand, TanStack Query |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic |
| GIS / Data | GeoPandas, Rasterio, Shapely, PyProj |
| Database | PostgreSQL, PostGIS |
| Real-time | WebSocket |
| Test | Vitest, React Testing Library, Playwright, Pytest |
| Deploy | Docker, Docker Compose, CI/CD |

## 19. 시스템 확장성

FloodOps는 홍수 도메인으로 시작하지만 구조적으로 다음 분야에 확장할 수 있도록 설계한다.

- 산불
- 산사태
- 도시침수
- 태풍
- 지진
- 교통재난
- 시설물 사고
- 스마트시티 관제

공통 구조는 다음과 같다.

```text
Observation
→ Spatial Analysis
→ Scenario
→ Intervention
→ Simulation
→ Comparison
```

## 20. 사업모델

### 기관용 FloodOps

연 단위 라이선스.

### 구축형

기관별 데이터·업무 프로세스 커스터마이징.

### Analysis Service

홍수 Scenario 분석 및 방재대책 비교 서비스.

### Digital Twin 구축

시설·도시·수자원 Digital Twin 프로젝트.

공모전 단계에서는 과도한 매출 추정보다 실제 기관 사용자가 어떤 의사결정을 더 빠르게 내릴 수 있는지 증명하는 데 집중한다.

## 21. MVP 범위

MVP에서는 아래 기능을 완성한다.

- 국내 홍수 사건 1개
- 2026 네팔 빙하 사건
- React + TypeScript
- MapLibre 기반 2D GIS
- FastAPI
- PostgreSQL + PostGIS
- 수문데이터 조회
- Flood Extent
- 주요 시설 공간분석
- Baseline Scenario
- Intervention 1~2개
- Before / After Comparison
- Observed / Derived / Simulated 구분
- 자동화 테스트
- 배포

Replay와 3D는 MVP 이후 추가한다.

## 22. Portfolio V1

MVP 완료 후 다음을 추가한다.

- 국내 + 해외 사건 2개
- WebSocket Historical Replay
- 3개 이상 Intervention
- Scenario 저장 및 재실행
- 대용량 공간데이터 최적화
- Playwright E2E
- 성능 Benchmark
- Architecture Documentation
- Data Provenance
- Public Live Demo

## 23. Advanced Version

- Cesium 3D Digital Twin
- 사건 3개 이상
- Evacuation Analysis
- 외부 Hydraulic Model Result 연동
- AI Situation Brief
- Simulation Job Queue
- Advanced Infrastructure Risk
- 최대 5개 사건

## 24. 차별화 포인트

FloodOps의 차별점은 다음과 같다.

- 단순 홍수 지도 시각화가 아니다.
- 단순 AI 재난 예측 시스템도 아니다.
- 실제 수문·공간 데이터를 이용해 현재 상황을 분석한다.
- 방재 개입 전후의 결과를 동일한 지표로 비교한다.
- Flood Decision Digital Twin으로 의사결정을 지원한다.

역할은 다음과 같이 구분한다.

| 구성요소 | 담당 역할 |
| --- | --- |
| GIS | 분석 |
| WebSocket | 관제 |
| Simulation | What-if 분석 |
| Digital Twin | 상황인지 |
| Intervention Comparison | 의사결정 |

## 25. 포트폴리오 핵심 메시지

FloodOps는 React와 TypeScript를 중심으로 GIS, PostGIS, FastAPI, WebSocket, 공간분석, Scenario Simulation, Digital Twin을 통합한 재난 의사결정 플랫폼이다.

단순히 재난을 시각화하는 데서 끝나지 않고,

> “어떤 대응을 선택하면 피해가 얼마나 감소하는가?”

를 계산하고 비교하는 것을 핵심 가치로 한다.

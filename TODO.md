# FloodOps TODO

Last Updated: 2026-09-02 23:25 KST

- Current identity: **Counterfactual Disaster Digital Twin PoC**
- Current MVP: **Historical Disaster Reconstruction + What-if Intervention**
- Reference case: `osong-2023`
- Core principle: FloodOps reconstructs what happened during the 2023 Osong disaster, then compares how response conditions could have changed under counterfactual interventions.
- Work sync rule: 작업 완료·상태 변경 시 TODO.md와 WORKLOG.md의 완료 여부 및 현재 상태가 서로 모순되지 않도록 함께 동기화한다.

## NOW

- Status: Active
- Last updated: 2026-09-02
- Next action: What-if A는 API로 연결됐다. 남은 것은 What-if B 가정 파라미터화, DQ-008을 반영한 영향 지표 설계, provenance 점검이다.

- [x] Historical Replay 완성
  - 실제 흐름: `강우 -> 미호강 수위 -> 월류 -> 임시제방 붕괴 -> 지하차도 유입 -> 주행 곤란 -> 완전 침수`
  - 지도 상태와 timeline 상태가 같이 변해야 한다.
  - 단순 뉴스 timeline처럼 보이지 않게 공간 상태 변화를 유지한다.
- [x] 현재 `approx_flood_envelope` 동작 검증
  - 현재 정의: `TEMPORARY + DERIVED + APPROXIMATION`
  - 용도: DEM low-elevation 기반 시간별 범람 근사 envelope
  - 금지: 실제 침수범위, 공식 Flood Extent, 실제 수심, 실제 유속, 정확한 침수예측으로 표현하지 않는다.
  - 현재 생성 결과: total 1,127 features; stage counts 36 / 96 / 182 / 241 / 270 / 298
- [x] HAND reconstruction 검증 및 비교
  - 현재 생성 결과: HAND grid 1,280 features; timeline 2,565 features
  - stage counts: 278 / 341 / 418 / 476 / 508 / 540
  - approx vs HAND comparison 생성 완료: final stage area 30.0194 km2 vs 54.3915 km2
  - 수위 관측값은 DEM 절대 수면고가 아니라 relative stage pressure로만 사용한다.
  - 공식 Flood Extent, depth, velocity, final exposure KPI로 사용하지 않는다.
- [ ] 실제 수위와 공간상태 연결 검증 보강
  - HAND reconstruction은 HRFCO 수위 변화와 사건 stage를 relative stage pressure로 연결했다.
  - 남은 검증: 관측소 기준면, 제방 붕괴 위치/폭, 유량, 배수시설, CCTV/공식 조사 timestamp 근거 연결.
  - 수위값 자체를 DEM 절대 수면고나 공식 침수심으로 해석하지 않는다.
- [ ] What-if 2~3개 구현
  - [x] A: 차량 진입 차단 시각 변경, 예: 08:25 / 08:30 / 08:35
    - `POST /api/events/{event_id}/analysis/closure-timing` 연결 (`feature/agent-tools`)
    - 산출: 차단 시점 사건 상태, 유입/주행불능/완전침수까지 남은 분, Scenario A(08:27 감지 차단) 대비 선행 시간
    - 08:25 차단 시 유입 2분 전, 완전침수 15분 전 확보. 08:35는 이미 주행불능 시점이라 선행 시간 -8분.
    - 관측 timestamp 간 산술만 수행한다. 차량 수, 사상자, 피해액은 산출하지 않는다.
  - [ ] B: 차수벽 설치 여부 또는 간단한 유입 감소 가정
    - 차수벽 높이에서 유입량을 계산할 유량/통수단면/조도가 없다.
    - 구현 가능한 형태: "유입 지연 Δt분"을 사용자 입력 가정으로 받아 timeline을 shift한다. 물리 계산이 아님을 응답에 명시한다.
  - [ ] C: 제방 조건 변경은 계산 근거가 충분할 때만 적용한다.
    - 붕괴 위치/폭/유량 미확보로 현재 보류 유지.
- [ ] DQ-008 대응: envelope 기반 영향 지표 설계
  - HAND final stage 54.392 km2 = AOI 40.557 km2의 1.34배. AOI 클립 후에도 읍 면적의 47.9%.
  - 그대로 중첩하면 건물 45.8%, 도로 50.5%가 영향으로 집계되어 근거로 제시할 수 없다.
  - 비파괴 경로: stage별 증분 지표 + 궁평2지하차도 중심 반경 제한 집계, `coverage_status` 명시.
  - envelope 자체 개선(붕괴 지점 기준 연결 성분 제약, AOI 클립)은 DECISIONS 기록 후 별도 branch에서 수행한다.
- [ ] Baseline vs Scenario 비교 고도화
  - 비교 가능: 대응 시작시점, 차단 상태, 위험구간 접근 가능 여부, 잠재 범람 envelope 차이
  - 금지: 사망자 감소, 피해액 감소, 실제 피해 감소율 임의 추정
- [ ] Provenance와 한계 표시 점검
  - Event Year, Data Vintage, Source, Role을 분리해 표시한다.
  - `approx_flood_envelope`는 공식 자료가 아닌 임시 파생 근사임을 UI에서 숨기지 않는다.

## BLOCKED

- Status: External dependency / missing validation material
- Last updated: 2026-09-01
- Next action: Keep these as validation or future analysis inputs; do not let them block observed reconstruction MVP.

- [ ] 2023 오송 실제 Flood Extent 공식 벡터 미확보
  - Current finding: DSSP-IF-00117 inventory 접근은 되었으나 2023 오송 직접 record는 확인되지 않았다.
  - Safemap `IF_0092_WMS`는 raster overlay로 연결되었지만 벡터 중첩 분석용 Flood Extent가 아니다.
  - Use: final validation / vector overlap analysis when acquired.
- [ ] 공식 세부 공간인구 미확보
  - Priority 1: 통계청/SGIS 등 한국 공식 세부 공간인구
  - Priority 2: 공식 읍면동 전체 인구 + WorldPop 공간분포 보정
  - WorldPop 단독은 fallback으로만 사용한다.
- [ ] CCTV 또는 공식 침수 진행 시각 원문 근거 미연결
  - 현재 timeline 값은 사건 재구성 기준으로 사용 중이다.
  - 공식 조사자료 원문 경로, page, timestamp 근거를 manifest/report에 연결해야 한다.
- [ ] 긴급재난문자 `DSSP-IF-00247` API 승인 대기
  - Current status: available key set 기준 `SERVICE_ACCESS_DENIED`
  - MVP 필수 입력은 아니며 Historical Replay 검증/보강용이다.

## NEXT

- Status: Ready after NOW
- Last updated: 2026-09-01
- Next action: Improve validation, error handling, and user-facing clarity after the MVP reconstruction loop is stable.

- [ ] HAND reconstruction을 official validation material과 비교
  - Safemap WMS raster 및 향후 official vector Flood Extent와 시각/공간 유사도를 비교한다.
  - gauge datum, breach geometry, discharge, drainage structure가 없다는 한계를 유지한다.
- [ ] 공식 Flood Extent 확보 후 geometry 중첩 분석
  - 대상: 공식 건물, 도로, 궁평2지하차도
  - 산출: 침수 건물 수, 침수 도로 길이, 지하차도 포함 여부
  - 공식 Flood Extent 전까지 노출 KPI는 `PENDING_FLOOD_EXTENT` 유지
- [ ] 직접 피해·구호 record 추가 검증
  - `DSSP-IF-10175` 피해침수
  - `DSSP-IF-10184` 재해구호상황보고
  - 공간 geometry가 아닌 피해 해석/검증 자료로 분리한다.
- [ ] 궁평2지하차도 별도 시설 모델링 보강
  - 공식 시설명, 노선, 관리기관, 위치, 시설 종류와 OSM geometry 결합 상태 점검
  - 차량별 노출/교통량 모델링은 아직 하지 않는다.
- [ ] API 오류 상태 테스트
  - missing layer, unavailable dataset, malformed processed file 상태를 테스트한다.
- [ ] Playwright E2E
  - `osong-2023` 진입, replay 실행, scenario 변경, layer toggle, provenance 표시를 검증한다.
- [ ] provenance 화면 고도화
  - 개발용 status보다 사용자 의미의 source, vintage, role, limitation을 우선 표시한다.

## LATER

- Status: Post-MVP
- Last updated: 2026-09-01
- Next action: Re-scope after the Osong reconstruction MVP is stable.

- [ ] HEC-RAS 2D 또는 LISFLOOD-FP 연계
  - Phase 2 physics-enhanced twin에서만 추진
  - 필요한 입력: 제방 붕괴 위치/폭/시간, 유량, 수위-유량 관계, Manning's n, 구조물, 검증 flood evidence
- [ ] 시간별 수심/유속 모델링
- [ ] calibration 및 실제 침수흔적 기반 validation
- [ ] 고급 What-if 분석
  - 제방 +0.5m / +1.0m
  - 차수벽 높이별 비교
  - 대응 정책 조합 비교
- [ ] 전국/다중 사건 확장
  - 2022 서울
  - 2022 포항
  - 2024 익산
  - 2026 안동·의성
- [ ] PMTiles / COG / vector tile 최적화
- [ ] PostGIS 적재 및 spatial query 최적화
- [ ] WebSocket 기반 고급 replay
- [ ] Predictive / Operational Twin
  - 실시간 센서
  - 기상예보
  - 자동 경보
  - 운영형 대응안 비교
- [ ] 공식 vs OSM 건물 일치율 QA 지표
  - `MATCHED`, `OFFICIAL_ONLY`, `OSM_ONLY` 비율을 포트폴리오 검증 지표로 산출

## DONE SUMMARY

- Status: Reference
- Last updated: 2026-09-01
- Next action: Detailed history remains in `WORKLOG.md`; dataset evidence remains in `data/manifests/` and processed validation reports.

- [x] `osong-2023`을 대표 reference case로 설정
- [x] processed data -> Backend Repository -> API -> React/Vite -> MapLibre 흐름 연결
- [x] Historical Replay API와 replay UI 연결
- [x] Baseline과 rule-based Intervention 1개 연결
- [x] KMA observed rainfall processed 연결
- [x] HRFCO/Flood Control Office observed water level processed 연결
- [x] WAMIS official river network 연결
- [x] SGIS 2023 Osong boundary 연결
- [x] Copernicus DEM low-elevation context 연결
- [x] official 2023-07 GIS Building Integrated Information processed building layer 연결
- [x] OSM historical snapshot 및 official building QA 생성
- [x] Safemap flood-mark WMS raster overlay 연결
- [x] `approx_flood_envelope` temporary derived approximation 생성 및 지도 연결
- [x] HAND-like reconstruction grid/timeline 생성 및 지도 연결
- [x] approx_flood_envelope vs HAND reconstruction 시간별 method comparison 생성 및 Replay UI 연결
- [x] data-quality issue tracking 문서 추가
- [x] README, Project Plan, Development Guide, Decision Records를 Counterfactual Disaster Digital Twin 정의에 맞춰 정리

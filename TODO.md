# FloodOps TODO

Last Updated: 2026-10-03 KST

- Current identity: **Counterfactual Disaster Digital Twin PoC**
- Current MVP: **Historical Disaster Reconstruction + What-if Intervention**
- Reference case: `osong-2023`
- Core principle: FloodOps reconstructs what happened during the 2023 Osong disaster, then compares how response conditions could have changed under counterfactual interventions.
- Work sync rule: 작업 완료·상태 변경 시 TODO.md와 WORKLOG.md의 완료 여부 및 현재 상태가 서로 모순되지 않도록 함께 동기화한다.

## NOW

- Status: Active / presentation-ready MVP
- Last updated: 2026-10-03
- Branch: 모든 작업은 `main` 하나에서 진행한다. 2026-09-06에 브랜치 4개를 `main`으로 정리했다.
- Next action: 공식 검증 자료 확보와 궁평2지하차도 시설 정보 점검을 이어간다. API 오류 상태, Playwright E2E, provenance 화면은 끝났다.

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
  - 현재 생성 결과(2026-09-30 미호천 기준 높이·연결 조건 적용 후): HAND grid 1,280 features; timeline 1,619 features
  - stage counts: 152 / 209 / 266 / 306 / 330 / 352 (이전 278 / 341 / 418 / 476 / 508 / 540)
  - approx vs HAND comparison(`osong_reconstruction_envelope_comparison.json`)을 2026-10-03에 09-30 HAND 기준으로 재생성했다. final stage area 30.0194 km2 vs 35.4577 km2(이전 54.3915).
  - 수위 관측값은 DEM 절대 수면고가 아니라 relative stage pressure로만 사용한다.
  - 공식 Flood Extent, depth, velocity, final exposure KPI로 사용하지 않는다.
- [ ] 실제 수위와 공간상태 연결 검증 보강
  - HAND reconstruction은 HRFCO 수위 변화와 사건 stage를 relative stage pressure로 연결했다.
  - 관측소 기준면은 이미 확보돼 있다: `data/raw/water_level/osong/hrfco_waterlevel_info.xml`의 미호강교(3011665) `gdt` 19.643 m, `pfh` 9.38 m → 계획홍수위 EL 29.023 m(국무조정실 발표 29.02 m와 일치). API 조회 시점 메타데이터라 2023년 당시 값과 같은지는 미확인.
  - 유량은 수위 CSV의 `fw_raw`에 있다(미호강교 08:00 6792.86). 관계곡선 환산값으로 보이며 단위 확인 필요.
  - [x] DEM(EGM2008)과 국내 표고 기준 차이 정리(2026-10-03, DQ-007 재검토): 오프셋 43.4 cm(부호 미확정, σ 18.5 cm)보다 Copernicus DSM 절대 오차(< 4 m LE90)와 하천 수면 편집값(18.0/18.5/19.0 m)이 훨씬 커서, 수위를 DEM 절대 수면으로 비교하지 않고 relative stage pressure를 유지한다. 절대 비교는 LiDAR DTM 확보 후.
  - 남은 검증: 제방 붕괴 위치/폭, 배수시설, CCTV/공식 조사 timestamp 근거 연결.
  - [x] 06:40/06:50 불일치 정리(2026-10-03, DQ-009): 06:40은 국무조정실 감찰 결과 발표 시각이다. 보관된 HRFCO 10분 자료로는 06:40 9.30 m(EL 28.943), 06:50 9.38 m(EL 29.023)이다. timeline은 발표 시각을 유지하고 관측 시각을 사건 설명에 함께 적었다. 차이의 원인(실시간/보정 자료, 1분/10분 자료)은 감찰 원문을 봐야 알 수 있다.
  - 수위값 자체를 DEM 절대 수면고나 공식 침수심으로 해석하지 않는다.
- [x] What-if 2개 구현 + 1개 보류
  - [x] A: 차량 진입 차단 시각 변경, 예: 08:25 / 08:30 / 08:35
    - `POST /api/events/{event_id}/analysis/closure-timing` 연결
    - 산출: 차단 시점 사건 상태, 유입/주행불능/완전침수까지 남은 분, Scenario A(08:27 감지 차단) 대비 선행 시간
    - 08:25 차단 시 유입 2분 전, 완전침수 15분 전 확보. 08:35는 이미 주행불능 시점이라 선행 시간 -8분.
    - 관측 timestamp 간 산술만 수행한다. 차량 수, 사상자, 피해액은 산출하지 않는다.
  - [x] B: 차수벽 설치 여부 또는 간단한 유입 감소 가정
    - `POST /api/events/{event_id}/analysis/inflow-delay` 연결
    - 구현 형태: `delay_minutes`를 사용자 입력 가정으로 받아 `underpass_inflow` 이후 timeline을 shift한다.
    - 0~180분 범위를 검증하며, 물리 계산이 아님을 응답의 assumptions/limitations에 명시한다.
    - 차수벽 높이에서 유입량을 계산할 유량/통수단면/조도가 없다.
    - 구현 가능한 형태: "유입 지연 Δt분"을 사용자 입력 가정으로 받아 timeline을 shift한다. 물리 계산이 아님을 응답에 명시한다.
  - [ ] C: 제방 조건 변경은 계산 근거가 충분할 때만 적용한다.
    - 붕괴 위치/폭 미확보로 현재 보류 유지.
    - 제방고는 언론 보도뿐이고 서로 어긋난다: 기존 제방 31.3 m·임시제방 29.7 m(노컷뉴스), "법정기준보다 1.14 m, 기존 제방보다 3.3 m 낮게"(대법원 2025도289 판결 보도). 판결문 원문(열람 신청 필요)으로 확정해야 한다.
- [ ] DQ-008 대응: envelope 기반 영향 지표 설계
  - [x] envelope 중첩 대신 사건 초점 시설 반경별 exposure inventory API와 Agent workflow를 연결했다.
  - exposure inventory는 침수 영향 추정이 아니라 반경 안의 건물·도로·시설 재고이며 `PENDING_FLOOD_EXTENT` 경계를 유지한다.
  - (09-30 이전 HAND 기준) final stage 54.392 km2 = AOI 40.557 km2의 1.34배. 그대로 중첩하면 건물 45.8%, 도로 50.5%가 영향으로 집계되어 근거로 제시할 수 없었다.
  - 비파괴 경로: stage별 증분 지표 + 궁평2지하차도 중심 반경 제한 집계, `coverage_status` 명시.
  - [x] envelope 개선 1차: 미호천 기준 높이 + 미호천·붕괴 셀 연결 조건(2026-09-30). final stage 540 → 352셀.
  - [x] AOI 클립과 개선 후 envelope의 면적·중첩 비율 재산출(2026-10-03): HAND final AOI 클립 15.434 km2 = AOI의 38.1%, AOI 안 건물 4,746/9,748동(48.7%), 도로 159.6/368.1 km(43.3%). 여전히 절대 노출 카운트로 쓸 수 없다. 09-02 비율은 AOI 밖 건물·도로까지 분모에 넣은 값이었다.
- [x] LLM intent planner 최소 연결
  - `backend/app/llm_planner.py` 신규. `POST /api/agent/plan`에 `planner: auto|deterministic|llm` 선택 추가.
  - LLM은 등록된 workflow 선택과 파라미터 추출만 수행한다. 분석 수치는 전부 결정론 Tool 결과를 사용한다.
  - 모델이 반환한 파라미터는 분석 endpoint와 동일한 범위(`radii_m` 50~20000, `delay_minutes` 0~180, `HH:MM`)로 재검증한다.
  - SDK/자격증명 부재나 검증 실패 시 결정론 planner로 폴백한다. `planner=llm` 명시 시에만 503으로 실패를 노출한다.
  - `GET /api/agent/planner-status`로 API 호출 없이 가용성을 조회한다.
  - 모델: `claude-opus-5`. `ANTHROPIC_API_KEY` 미설정 시에도 서비스는 정상 동작한다.
- [x] Agent 거절 응답에 인접 질문 제시
  - `AgentIntentPlanResult.suggestions`로 답할 수 있는 질문을 함께 반환한다.
  - `UNSUPPORTED`는 전체, `NEEDS_CLARIFICATION`은 감지된 후보 워크플로만, `READY`는 빈 배열이다.
  - `GET /api/agent/examples`가 시작 칩과 제안 문구의 단일 출처다. 문구 4개가 실제로 라우팅되는지 테스트로 고정했다.
- [x] LLM planner 오프라인 폴백 시간 제한
  - `timeout` 기본 10초(`AGENT_LLM_TIMEOUT_SECONDS`), `max_retries=0`.
  - SDK 기본값(timeout 10분·재시도 2회)에서는 망 불통 시 폴백에 도달하지 못하고 요청이 멈춘다.
  - 불통 주소에서 timeout 3초로 재현해 3,379ms 내 규칙 planner 폴백을 확인했다.
- [x] LLM planner 경로에 거부 게이트 적용
  - `plan_with_llm`이 `_UNSUPPORTED_MARKERS`를 사용자 원문에 먼저 검사하고, 걸리면 모델 호출 전에 `UNSUPPORTED`로 반환한다.
  - 모델이 표현을 바꿔 거부를 피해가는 경로를 막는다. 검사는 모델 출력이 아니라 원문 기준이다.
- [x] `situation` 워크플로 응답 계약 결손 보정
  - 워크플로 결과에 `coverage_status: fallback`과 재구성 시각이 `NEEDS_SOURCE_PAGE`라는 `coverage_note`를 붙였다.
  - 계획 단계 `assumptions`에 저장된 재구성 시각만 보여준다는 점과 HAND 근사 envelope임을 명시했다.
- [x] 지도 출처 표시
  - 관제·비교 지도에 OSM(ODbL)·국토교통부 GIS건물통합정보·WAMIS 출처를 접지 않은 상태로 표시한다.
- [x] Agent intent planner 한국어 평가셋
  - 15개 질문에 대해 기대 status, workflow, 파라미터, Tool sequence를 fixture로 고정했다.
  - 사망자·피해액·침수심·예측 요청은 다른 marker보다 우선해 `UNSUPPORTED`로 거부한다.
- [x] Portfolio response scenario API
  - `POST /api/scenarios`로 건물 ID와 복수 intervention을 DRAFT로 저장한다.
  - `POST /api/scenarios/{scenario_id}/run`으로 대응 전후 priority building과 rule-based risk score를 비교한다.
  - 현재는 HAND-like envelope 기반의 `TEMPORARY` 의사결정 보조 결과이며, 공식 피해 감소율이 아니다.
- [x] Dark console UI 미리보기 마감
  - `src/dark/`에 관제 화면, 단면도 시각화, exposure inventory 패널을 추가했다.
  - `CrossSection`을 `hand_reconstruction` 레이어에 연결해 단계별 관측 수위 상승분과 HAND 임계를 시각화한다.
  - 왼쪽 판단 탭에 대응 시점·공간 상태·반경별 재고·Agent를 중요도 순으로 배치하고, 지도 오버레이를 축소했다.
  - 반경별 재고 표는 기본 화면에서 제거하고 Agent 질의로 전환했으며, Layers는 접이식 설정으로 유지했다.
  - Agent를 왼쪽 판단 탭 상단으로 이동해 기본 화면에서 바로 보이게 했다.
  - `Scenario 비교` 탭을 추가해 원시나리오와 감지 자동차단 개입을 별도 비교 화면에서 확인할 수 있게 했다.
  - 비교 화면은 대응 상태 변화와 침수 진행이 변하지 않는 부분을 분리해서 표시한다.
  - 기존 light UI와 backend/API를 재사용하는 presentation layer이다. 2026-09-06에 `main`으로 병합됐다.
  - 반응형 CSS와 라이트 UI glyphs 설정은 반영했다.
  - 2026-10-02 Edge 브라우저 smoke test: 인트로(1280×720 스크롤 없음) → 사례 선택 → 관제 화면 7단계 재생·레이어 설정 → 시나리오 비교(지도 2개) → 인사이트까지 콘솔 오류 0건, API 4xx/5xx 0건.
- [x] 로컬 런타임 포트 고정
  - FloodOps FastAPI `8033`, Vite `5173`을 사용한다.
  - 다른 프로젝트가 사용하는 `8000`으로 잘못 연결되어 `/api/events`가 404가 되던 문제를 해결했다.
  - Vite는 `strictPort`로 설정해 5173이 사용 중이면 5174로 자동 이동하지 않는다.
- [ ] Baseline vs Scenario 비교 고도화
  - 비교 가능: 대응 시작시점, 차단 상태, 위험구간 접근 가능 여부, 잠재 범람 envelope 차이
  - [x] `compare_scenarios` Tool 최소 구현: closure timing/inflow delay의 baseline 대비 시간 비교
  - [x] UI `Scenario 비교` 탭: 원시나리오·개입 시나리오 카드와 비교 매트릭스
  - 금지: 피해액, 사상자, 실제 침수면적·침수심 감소율 추정
  - 금지: 사망자 감소, 피해액 감소, 실제 피해 감소율 임의 추정
- [x] Provenance와 한계 표시 점검
  - 2026-10-02 화면 확인: timeline 단계마다 "출처 쪽수 확인 필요", 공간 상태에 "HAND 근사", 단면 임계에 "실측 수위가 아님", 비교 화면에 "실제 침수 위험 감소가 아님"이 표시된다.
  - Event Year·Data Vintage·Source·Role 분리 고도화는 NEXT의 provenance 화면 고도화로 이어간다.

- [x] 2022 서울 도림천 유역 사례 연결 (2026-10-03)
  - 범위: 경도 126.89~126.955, 위도 37.465~37.51 bbox(28.69 km2). 도림천 본류와 신림·신대방·대림 포함.
  - 공식 침수흔적도 2022: 범위 안 10,468건, 합친 면적 2.556 km2, 침수심 중앙값 0.2 m·최대 1.0 m. 상세 주소(`F_ZONE_NM`)와 지번은 제외했다.
  - 건축물: GIS건물통합정보 2026-08-09 스냅샷에서 사용승인 2022-08-08 이후 47동 제외, 재고 66,099동 중 흔적과 겹친 13,015동(19.7%).
  - 강우: 서울시 10분 강우계 6곳. 신림P 60분 최대 121.5 mm(20:59 종료), 95 mm/h 초과 20:49.
  - 사건 단계 7개: 12:50 호우경보, 13:09 50 mm/h, 20:49 설계강우 초과, 20:59 첫 구조 신고, 21:19 첫 저지대 문자, 21:30 중대본 2단계, 21:45 소방 도착. 강우 임계 외에는 언론 보도 시각이다.
  - 반사실 A `POST /api/events/seoul-2022/analysis/alert-timing`: 95 mm/h 도달 경보는 첫 신고 10분 전, 실제 문자보다 30분 빠름.
  - 반사실 B `POST /api/events/seoul-2022/analysis/storage-capture`: 40만 m3 터널, 95 mm/h, 유출계수 1.0이면 초과량 870,263 m3 중 46.0%, 20:49 만수.
  - Agent는 서울을 지원하지 않는다. 반경 재고(`exposure-inventory`)는 서울에서 404를 유지한다.
- [ ] 서울 사례 보강
  - 언론 보도 시각을 공식 원문으로 교체한다. 2026-10-03: 중대본 2단계는 행안부 보도자료로 바꿨다(오전·오후 미표기). 첫 신고 20:59는 중대본 보고의 '21:07경'과 어긋나 병기했다. 12:50 경보, 21:19 문자, 21:45 소방 도착은 원문 미확보.
  - 도림천 수위(신대방1교 등) 2022-08-08 이력을 정보공개로 확보한다. 공개 API는 최신값만 준다.
  - [x] 저류 계산 면적을 도림천 유역면적 40.96 km2(김재근 외 2012, 이승종 외 2005 인용)로 바꿨다(2026-10-03). 공식 하천기본계획 값으로 교체할 여지는 남음. bbox 28.69 km2는 선택지로 유지.
  - [~] 신월 저류시설: 32만 m3·시간당 95~100 mm는 서울시(내 손안에 서울 2022-08-10)로 확인, 8.8 유입 224,929 m3는 언론만 확인. 참고 사례 카드로 붙였다(다른 유역이라 검증 아님).

- [x] 포항 2022·안동·의성 2026 사건 시각형 사례 연결 (2026-10-03)
  - 공통 모듈 `backend/app/timeline_cases.py`, 공통 화면 `src/dark/TimelineConsole.tsx`, `POST /api/events/{id}/analysis/response-timing`.
  - 포항: 04:50 태풍 상륙 ~ 07:40 실종 신고 8단계. 진입 금지 안내를 06:00(범람 시작)에 했다면 침수 시작 37분·완전 침수 45분 전. 실제 06:30 안내는 7분 전이었다.
  - 안동·의성: 7/18 22:59 첫 고립 ~ 7/19 08:00 산사태 위기경보 '경계' 7단계. 대피명령을 23:40 경보와 동시에 냈다면 경보 수위 도달 예측(00:30)까지 50분, 실제 00:00은 30분.
  - 지도는 사건일 OSM 스냅샷(포항 2022-09-06, 안동 2026-07-17)과 보도된 지명 중심점만. 건축물 OSM은 66동·23동뿐이라 노출 집계를 하지 않는다.
- [ ] 포항·안동 보강
  - 기상청 AWS(포항 오천·동해·구룡포, 안동 남선·의성 비안) 10분/1시간 자료를 자료개방포털에서 받아 강우 그래프를 붙인다.
  - 미천 운산리 수위(낙동강홍수통제소) 2026-07-18~19 자료를 홍수통제소 API로 받아 00:30 예측과 실측을 대조한다.
  - 사건 시각을 공식 원문(판결문, 홍수통제소 발령 이력, 중대본 보고)으로 교체한다.

- [x] Agent 다중 사례 확장 (2026-10-03)
  - `backend/app/agent_cases.py`: 사건별 도구 목록·값 검증·라우팅 힌트·예시 질문. 오송 도구 목록과 동작은 그대로다.
  - 서울: `analyze_alert_timing`, `analyze_storage_capture`. 포항·안동: `analyze_response_timing`. 공통: `get_reconstruction`, `get_observation_summary`(서울 강우·흔적 노출, 포항·안동 보도 수치).
  - 모델 값 검증: 시각은 질문·사건 단계 시각·"N분 일찍" 환산값만, 강우 임계는 질문에 쓴 mm만, 저류량은 질문 값 또는 등록값(40만·32만 m3)만. 다른 사건의 도구는 거부한다.
  - `GET /api/agent/examples?event_id=`로 사건별 시작 질문, 서울·포항·안동 화면 상단에 Agent 입력창.

- [x] 사례 간 비교 화면 (2026-10-03)
  - `GET /api/cases/lead-times`: 각 사례 계산 함수를 그대로 호출해 실제·반사실 대응의 기준 사건 대비 선행 분을 낸다.
  - 오송 실제 통제 없음 → 06:40 통제면 유입 107분 전. 서울 실제 21:19(-20분) → 20:49(10분). 포항 06:30(7분) → 06:00(37분). 안동 00:00(30분) → 23:40(50분).
  - 덤벨 차트(실제 #d97014 원, 반사실 #109c8e 마름모, 다크 배경 팔레트 검증 통과) + 같은 값의 표 + 툴팁. 사례 간 순위 비교는 하지 않는다고 명시.

- [x] 서울·포항·안동 재생 시 지도 변화 + 시나리오 비교 탭 통일 (2026-10-10, DQ-012)
  - 서울: 공식 침수흔적도를 95 mm/h 초과 뒤 깊은 곳부터 드러냄(0 → 1,557 → 10,468건). DSM HAND envelope은 흔적 대조에서 무의미(14~16%)해 싣지 않음.
  - 포항: 냉천교에서 퍼지는 HAND 근사 셀 0·0·78·120·144·175·175·175. 안동: river 선 띠 605·952·973·1,035·1,073·788·265.
  - 남은 것: 포항·안동에 관측 강우·수위가 연결되면 보도 순서 임계를 관측 기반으로 교체. 구계리는 재현 안 됨.
- [ ] 공개 서버에서 서울·포항·안동 사례 열기 (2026-10-09 준비, 배포 전)
  - 공개 서버는 10-01 빌드라 세 사례의 `/reconstruction`이 404다. 현재 `main`으로 이미지를 다시 빌드해 컨테이너를 교체해야 한다.
  - [x] `.dockerignore`가 `seoul_2022` 폴더를 제외하던 결함 수정, `docs/DEPLOY_AWS.md`에 재배포 체크리스트 기록, `e2e/other-cases.spec.ts`로 세 사례 진입·반사실 비교 검증(9개 통과).
  - 측정: 레이어 gzip 오송 1.07·서울 1.18·포항 0.03·안동 0.12 MB, 네 사례 로드 후 RSS 364 MB(상한 600 MB).
  - 필요: `aws login` 브라우저 승인과 배포 실행 승인. 배포 뒤 네 사례 `/reconstruction` 200과 `docker stats` 확인.
- [ ] 공개 사이트 방문 통계·검색 등록·광고 측정 (2026-10-03 코드 준비, 배포 전)
  - 준비됨: `robots.txt`, `sitemap.xml`, `meta description`·canonical·Open Graph(1200×630 `og-image.png`), GA4·메타 픽셀 동의 배너, 개인정보 안내 `#privacy`, 서치 콘솔 HTML 태그 빌드 주입.
  - 필요: GA4 측정 ID, 메타 픽셀 ID, 서치 콘솔 인증 값, 문의처. 받은 뒤 `--build-arg`로 이미지 재빌드·배포(배포는 별도 승인).
  - 배포 뒤: 서치 콘솔에 `https://floodops.duckdns.org/sitemap.xml` 제출, GA4 실시간 보고서로 수집 확인, 메타 이벤트 관리자에서 PageView 확인.
  - Lighthouse 12(로컬 Edge, 소개 화면) 기준선: 모바일 성능 94·SEO 90, 데스크톱 성능 100·SEO 90. SEO 감점은 `meta description` 부재(이번에 추가).
  - 관제 화면(공개 서버, 2026-10-04): 오송 레이어 응답 gzip 4.0 MB를 받는 데 9.4초(TTFB 0.11초). 첫 측정은 167초(재시작 직후로 추정). 레이어 응답을 화면이 쓰는 속성·좌표 5자리로 줄여 1.06 MB로 만들었다(배포 전).

## BLOCKED

- Status: External dependency / missing validation material
- Last updated: 2026-09-04
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
- Last updated: 2026-10-03
- Next action: Improve validation, error handling, provenance, and E2E coverage after the presentation-ready MVP.

- [x] README/TODO implementation status synchronization
  - Current MVP, Agent planner, scenario API, Swagger routes, and known limitations are documented.

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
- [x] API 오류 상태 테스트 (2026-10-03)
  - 누락된 오송 레이어는 `UNAVAILABLE`/`MISSING_PROCESSED_FILE`, 손상된 GeoJSON은 `UNAVAILABLE`/`MALFORMED_PROCESSED_FILE`로 반환하고 빈 FeatureCollection을 제공한다.
  - 연결되지 않은 익산 데이터셋은 `UNAVAILABLE`, 등록되지 않은 사건은 404로 응답하는 것을 확인했다.
  - `python -m pytest backend/tests -q`: 116개 통과.
- [x] Playwright E2E (2026-10-03)
  - `osong-2023` 진입, 7단계 replay 실행, HAND 레이어 토글, 사건 시각 근거와 지도 출처 표시를 Chromium에서 검증했다.
  - 통제 시각을 08:09로 변경해 유입 18분 전이라는 비교 결과와 침수 진행 한계 표시를 검증했다.
  - `npm run test:e2e`: 3개 통과. `npm test`: 2개 통과. `npm run build`: 통과.
- [x] provenance 화면 고도화 (2026-10-03)
  - 오송 `출처·한계` 탭에서 API의 7개 자료에 대해 역할·출처·자료 시점과 재구성 한계 5개를 함께 표시한다.
  - 인사이트의 `TEMPORARY`/source_type 개발용 문자열 대신 사건 연도, 관측 입력 출처, HAND 지도 출처를 표시한다.
  - Chromium E2E에서 출처·자료 시점·역할·한계 표시를 확인했다.

## LATER

- Status: Post-MVP
- Last updated: 2026-09-04
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
  - [x] 2022 서울 도림천 유역 (2026-10-03, 관제·반사실 화면까지 연결. NOW의 서울 항목 참고)
  - [x] 2022 포항 냉천·인덕동 (2026-10-03, 사건 시각 재생 + 진입 금지 안내 시각 반사실)
  - [ ] 2024 익산: 피해는 함라가 아니라 산북천 유역(낭산·망성). 2026-10-03 재조사에서도 특보·재난문자·제방 붕괴 시각을 찾지 못함(망성 주민 '04:00 대피소 도착' 진술 1건). 기상자료개방포털 특보 이력, 국민재난안전포털 재난문자 조회, 익산시 보도자료로 확인 전까지 잠금 유지
  - [x] 2026 안동·의성 (2026-10-03, 사건 시각 재생 + 대피명령·산사태 위기경보 시각 반사실)
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
- Last updated: 2026-09-04
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
- [x] closure-timing / inflow-delay What-if API와 `compare_scenarios` Tool 연결
- [x] LLM intent planner, deterministic fallback, 한국어 평가셋 연결
- [x] portfolio response scenario API와 Swagger contract 연결
- [x] data-quality issue tracking 문서 추가
- [x] README, Project Plan, Development Guide, Decision Records를 Counterfactual Disaster Digital Twin 정의에 맞춰 정리

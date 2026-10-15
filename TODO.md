# FloodOps TODO

Last Updated: 2026-10-14 KST

- Current identity: **지하차도 통제 판단 트윈 PoC** (아래 DIRECTION 기준)
- Current MVP: **지금 상태 보드 + 시설 관측·판정·백테스트 API + 시설 Agent + 과거 사건 재구성·What-if 화면**. 보드의 공간 상태 표시와 기존 탭 재배치는 남아 있다.
- Reference case: `osong-2023`
- Core principle: 시설의 관측·통제 검토 규칙을 연결하고 과거 사건으로 백테스트한다. 과거 사건 재구성과 통제 시각 비교는 검증 기능으로 유지한다.
- Work sync rule: 작업 완료·상태 변경 시 TODO.md와 WORKLOG.md의 완료 여부 및 현재 상태가 서로 모순되지 않도록 함께 동기화한다.

## MILESTONES (2026-10-14 · 2차 제출 계획)

- Status: Active / 공고 일정 기준(2026-10-14 확인). 1차 교류회 날짜는 미확인
- 일정: 1차 교류회·멘토링 10월 중 → **상세기획서 정식 제출 11/3(화)**(+선택 참고자료 200 MB) → 예선 심사 11/4~6 → 2차 교류회·멘토링 11월 중 → 본선 12월 초(발표자료 + 서비스 결과물, 본선 10팀)
- 배점: 예선 = 기획성 30·활용성(플랫폼) 20·유용성 20·협력성 15·충실성 15 / 본선 = 기획성 15·완성도 25·확장성 25·유용성 25·발표 10. 11/3까지는 예선 배점 순, 그 뒤는 본선 배점 순으로 우선한다. 발표자료 v5는 본선 배점 순서다.
- 9/30에 낸 상세기획서는 조기 제출본이다(9/30의 공식 제출물은 참가신청서). 11/3 정식 제출로 교체되는지 «작품접수 및 확인» 메뉴 또는 사무국(02-2052-1267, support@cccr.or.kr)에 확인한다.
- 개발 동결 제안: 10/27(월). 그 뒤 11/3까지는 기획서·참고자료만 만든다.

### A. 1차 교류회 전 (10월 중, 날짜 확인 필요)
- [ ] 사무국 확인 3건: 1차 교류회 날짜, 9/30 상세기획서 교체 가능 여부, 플랫폼 자원(클라우드·AI·위기 데이터 609종) 신청 승인 상태. [활용성·충실성]
- [x] 교류회 3분 자료(2026-10-14, `FloodOps-2026-v5/FloodOps_교류회3분_v5.pptx`·`.pdf`, 대본 `Meetup_3min_Script.md` 40/60/40/40초, `fitWarnings=0`): v5에서 당직 장면(19장)·보드 화면①(8장)·기준 맞바꿈(20장) 3장 + «도움 요청» 1장. 보드 화면을 관제 화면 틀로 다시 짜면 2장 캡처를 다시 찍는다(관리대장·센서 설치 여부·시각 있는 통제 이력·실무 인터뷰 2건). `FloodOps_Meetup_3min_Dense_v2`는 사건 뷰어 방향이라 쓰지 않는다. [협력성·유용성]
- [ ] 공개 서버에 트윈 보드 올리기: 현재 서버는 10-01 빌드라 `#twin`이 없다. 같은 컨테이너 교체이고 서버 추가·사양 변경 없음(크레딧 한도). `docs/DEPLOY_AWS.md` 체크리스트대로, `aws login`·배포 실행은 사용자 승인 뒤. 완료 근거: 공개 URL에서 `/api/twin/facilities` 200, `#twin` 3탭 스모크(`e2e/twin-board.spec.ts` 흐름). [충실성·완성도]
- [ ] 인터뷰 질문지·기록 양식 준비: `docs/MARKET_VALIDATION.md` 20분 질문 + `docs/market-validation/` CSV. 교류회에서 지자체 재난·도로 담당자 2명 이상 기록(날짜·참여자·의견·반영). 1차 기획서의 협력 활동 표가 약속한 «검토 기록». [유용성·협력성]
- [ ] 홍수통제소에 미호강교(3011665) 2023-07 당시 경보·계획홍수위 기준값과 2023-07-15 새벽 10분 수위의 실시간 제공 시각(지연·결측) 문의. 157분은 2026-10에 다시 받은 보관 자료와 현재 기준값(경보 8.0·계획홍수위 9.38 m)으로 계산했기 때문에, 답을 받아야 한계 문구의 «미확인»을 «확인»으로 바꿀 수 있다. [충실성·기획성]
- [x] 157분 한계 명시(2026-10-15, 외부 평가 지적): ① 보관 자료로 계산 ② 기준값은 현재 값 ③ 06:40 발표 vs 06:50 보관 자료(DQ-009) ④ 2023-05-16 센서 오류 격리 ⑤ 직전 30분만 사용(미래 값 미사용). 반영: Agent 백테스트·기준 비교 답변에 서버 단서(`agent_facility.archive_caveat`), `docs/PLAN_UNDERPASS_TWIN.md` §6 표, 상세기획서 초안 백테스트 절, 발표 v5 10장 하단·결론·노트, 교류회 3분 자료 3장 결론·대본(«보관 수위로 다시 돌리면», 40초 유지), 두 덱 모두 `fitWarnings=0`. 교류회 1·2장의 «유입 157분 전» 표기는 3장 단서에 맡기고 그대로 두었다. [충실성]
- [ ] 2025-07-17 궁평2지하차도 통제·침수 여부 문의(충북도로관리사업소). 기준 검토 탭 «다른 해 1건»을 «불필요한 통제»/«필요했던 통제»로 바꿀 근거. [유용성]
- [ ] 미커밋 작업 정리: 라이즈 모델·`twin.py`·문서(다른 도구 작업)와 글꼴·기획안·v4/v5 발표자료를 묶어 커밋. 커밋안 확인 뒤 푸시. [충실성]

### B. 상세기획서 11/3 전 (예선 배점 순)
- [~] [기획성 30] 2차 상세기획서 초안(md → 한글, 2026-10-14 초안 `docs/submission/detailed-plan-2026-11-03-draft.md`, `[기입]` 자리 남음): 제출 목차 그대로(추진배경·개요·협력 방안·플랫폼 활용·개발 환경·내용·운영 계획·기대효과). «1차 대비 변경점» 절 추가 — 사건 뷰어 → 시설 트윈, 재생 모드 = 훈련 기능 유지, 서울·포항·안동은 검증 사례로 축소, 익산 제외 이유(시각 근거 없음). 근거는 `docs/PLAN_UNDERPASS_TWIN.md`.
- [ ] [활용성 20] 플랫폼 자원이 승인되면 같은 Docker 이미지를 플랫폼 클라우드(네이버·KT·NHN 중 지원사)에 배포하고 접속 URL을 기획서에 적는다. 승인 전이면 «신청 상태»를 그대로 적고 추정하지 않는다.
- [ ] [활용성 20] 플랫폼 위기 데이터 1종 이상 연결: 후보 홍수예보발령(홍수통제소)·기상특보(기상청)·재난문자 발령현황(행안부). 보드 «지금 상태»에 «공식 발령» 줄로 규칙 단계와 나란히 표시(규칙을 대체하지 않음). 카탈로그(홍수침수 62종)에 지하차도 침수 센서·진입차단 자료가 있는지도 확인.
- [ ] [유용성 20] 교류회 인터뷰 2건 이상을 기획서 «협력 활동» 표에 날짜·참여자·의견·반영으로 기입. 없으면 «미실행»으로 둔다.
- [ ] [협력성 15] 기관 요청 1건 이상 발송 기록: 충북도로관리사업소(궁평2 관리대장·2025-07-17 통제 이력) 또는 서울시설공단(지하차도 센서·통제 이력). 회신 전이면 «요청 중»으로 적는다.
- [ ] [충실성 15] 1차 기획서 약속 대조표를 기획서에 넣는다: «상세기획서까지 완료할 기능» 4개 — 사고 시각 원문 출처 연결(DQ-005, 미완), 거절 규칙 보강(완료), 사건마다 동일 데이터 형식·검증 기준(→ 시설 등록 형식으로 대체), AWS 배포·접속 확인(재배포 필요).
- [ ] [충실성 15] 원문 2건 확보: 행안부 지하차도 통제 기준 5 cm(보도자료·지침)와 국무조정실 감찰 결과의 사건 시각 쪽수.
- [x] [확장성] 시설 등록 형식 문서화 `docs/FACILITY_REGISTRY.md`(2026-10-14): `FACILITIES`를 `data/facilities/registry.json`으로 옮기고 관문 4개(유입 경로·대표 관측소·현장 계측·검증 사건, CONFIRMED/PENDING/MISSING/UNKNOWN)와 `CANDIDATE` 상태를 넣었다. 로더 `backend/app/facility_registry.py`(후보에 임계·규칙이 들어오면 거부), `GET /api/twin/registry`, 후보 id의 시설 엔드포인트는 409 `FACILITY_NOT_OPERATIONAL`, 보드 시설 카드에 관문 칩. 테스트 8개 추가(전체 226 통과). 내수 배수형은 아직 정의만.
- [~] [확장성] 충북 후보 32곳 중 홍수예보 지점 5 km 안 시설을 추려 1곳의 관문(유입 경로·대표 관측소·현장 계측·검증 사건)을 조사한다. 검증 사건이 없으면 «후보(검증 사건 없음)» 상태로 레지스트리에 올릴지는 사용자 결정.
  - 2026-10-14: `data/scripts/build_facility_candidates.py`로 후보 5곳 생성 — 청주 오송바이오폴리스(519)·용암(521)·학평(523), 영동 심곡(921, 초강교 4.22 km), 청주 궁평(933, 미호강교 1.16 km·좌표가 궁평2와 겹쳐 확인 필요). 계룡(916)은 OSM 좌표가 대전 유성구라 제외(`excluded`에 이유). 충북 32행 중 좌표 있는 행은 6행뿐이라 나머지는 지오코딩 뒤 재생성. 관문 조사는 아직 0곳.
- [ ] [완성도] 기상청 AWS 10분 강우 실시간 연결(`KMA_API_HUB_KEY` 발급 뒤). 실시간 모드에서 강우 카드가 `NEEDS_DATA`가 아니게. 내수 배수형 규칙의 입력.
- [ ] 참고자료 zip(≤200 MB): 보드 3탭 캡처, `/api/twin/...` 응답 샘플, 테스트 로그(백엔드 178·E2E 11), 공개 URL, v5 PDF.

### C. 예선 뒤 ~ 본선 12월 초 (본선 배점 순)
- [~] [완성도 25] **재배포 전 메모리(2026-10-15)**: 현재 작업 트리 이미지가 스왑 없는 600 MB 컨테이너에서 첫 Agent 질문 때 OOM 종료(exit 137)되는 것을 로컬 Docker로 확인했고, 오송 저장소 캐시 키 통일(같은 ~140 MB 자료를 반복 파싱하던 버그)·지도 gzip 단일 캐시·읽기 전용 공유 뷰로 고쳐 같은 조건에서 통과했다(정착 663→506 MiB, 상한 도달 0회, `docs/AGENT_OPTIMIZATION_LOG.md` 5단계). 남은 일: 재배포 직후 EC2에서 `docker stats`로 같은 흐름 확인. 여유를 더 원하면 `lightgbm`(88 MB) 대신 순수 파이썬 트리 평가(연구 모델 파일 작업이 커밋된 뒤). [완성도]
- [x] Gemini 3주차 최종 상태 live 43문항 재확인(2026-10-15 16:06, 할당량 초기화 후): 43/43, 토큰 218,766(−21.4%). 앞선 2회는 HTTP 429로 무효. [완성도]
- [ ] [완성도 25] 공개 서버 안정화: 재배포 뒤 `docker stats`·RSS 상한 600 MB 확인, 실시간 모드(홍수통제소 키)와 재생 모드 전환 확인, 장애 시 데모 백업(로컬 2023 재생 + 녹화 영상).
  - 알려진 E2E 실패(2026-10-14, HEAD 3c9fb91에서도 재현): `e2e/agent-conversation.spec.ts:89` 서울 사례 전환이 `layers?layer_year=2022` 응답 15.2 MB·서버 5.0초 때문에 15초 expect를 넘긴다. 서울 레이어 축소(오송처럼 속성·좌표 자리수 정리) 또는 expect 조정. 나머지 E2E 15개는 통과.
- [ ] [확장성 25] 내수 배수형 규칙 v1: 기상청 10분 강우 강도(서울 2022 분석의 95 mm/h 임계 재사용) + 호우특보. 서울 지하차도 1곳을 후보로 등록해 두 유형이 같은 형식임을 보인다. 기후에너지환경부 도시침수예보(서울 강남·서초·관악·구로·동작·영등포, 10분 주기)는 입력 후보로 조사.
- [ ] [확장성 25] 백테스트 정답지: 서울시설공단 «자동차전용도로 침수 기록»(2016~, 28행, 일자·노선·방향·구간만)은 날짜 수준 대조에만 쓴다. 시각 있는 지하차도 통제 이력은 기관 협력으로만 확보.
- [ ] [유용성 25] 2차 교류회(11월 중) 파일럿: 같은 2023 재생으로 기존 방식 ↔ 트윈 순서 교차, 2~3명이라도 실제 기록(판단 시간·근거 이해·오해 여부). 결과가 생기면 v5 22장을 결과로 교체.
- [ ] [발표 10] 본선 발표자료: v5를 결과(배포 URL·인터뷰·파일럿·추가 시설·플랫폼 연결)로 갱신. 15분 리허설.
- [ ] LISFLOOD-FP는 제방 붕괴 폭·위치 원문이 없으면 본선 범위에서 뺀다(가정 민감도 이상을 주장하지 않음).

### 조사 결과 (2026-10-14, 지하차도 침수 센서 자료)
- 기상청 API허브·공공데이터포털의 방재기상관측(AWS)은 강수·바람·기압·습도 등 기상 요소만 제공한다. 침수 센서 항목은 없다. 하천 수위는 홍수통제소(연결됨).
- 지하차도 침수 센서·진입차단시설의 실시간 공개 API는 찾지 못했다. 서울시는 중점관리 95곳 중 94곳에 스마트 진입차단시설 가동(2025-10-26 보도: 바닥 센서 2개 이상·3초 이상 감지 → 상황실 신호 → 조치 없으면 자동 차단). 자료 공개 여부는 보도에 없음.
- 서울시설공단 공개 자료: 터널·지하차도 CCTV 현황(연 1회), 자동차전용도로 침수 기록(2016~, 28행, 일자·노선·방향·구간). 시각·수심·지하차도 구분 없음.
- 기후에너지환경부 도시침수예보: 서울 6개 구, 강우·도로 지도·CCTV·수위계로 10분마다 자동 분석·예측(2026-07 보도). 제공 채널·API·지하차도 포함 여부 미확인.
- 결론: 센서는 하천 수위를 대체하지 않고 보완한다. 센서·차단기 = «지금 들어왔나»(현장 설비, 이미 있음), 하천 수위 = «몇 분 남았나»(FloodOps). 센서 이력은 다른 시설 규칙의 검증 정답지이며 기관 협력으로만 받는다.

## DIRECTION (2026-10-10 방향 재설정)

- Status: Decided in principle / 사용자 확정 대기 항목은 아래 "확정 필요"
- Last updated: 2026-10-10
- 배경: 현재 제품은 과거 사건 4개를 재구성해 보여주는 뷰어에 가깝고, 제출 기획서의 정체성(홍수 대응 의사결정 디지털트윈, 주사용자 지자체 재난·도로 담당자, 핵심 기능 지하차도 통제 시각 비교)과 PROJECT_PLAN의 Phase 2(물리 모형)·Phase 3(운영 트윈)으로 가지 못했다. 훈련 시뮬레이터 방향은 가지 않는다.
- 정의: **지하차도 통제 판단 트윈.** 트윈의 단위는 사건이 아니라 시설(지하차도)이다. 관측(수위·강우)으로 지금 어느 단계이고 유입·통제 기준까지 몇 분이 남았는지를 보여주고, 통제 기준을 과거 사건으로 백테스트해 검증한다. 반사실(통제 시각 비교)은 그대로 핵심 기능으로 남긴다.
- 사례의 역할 변경: 오송 2023은 첫 시설(궁평2지하차도)의 검증 사건이다. 서울·포항·안동·의성은 별도 관제 화면이 아니라 "검증 사례" 한 페이지(현재 `GET /api/cases/lead-times`)로 내린다. 익산처럼 시각 근거가 없는 사례는 뺀다. 포항·안동의 보도 순서 HAND 띠는 트윈 화면에서 쓰지 않는다.
- 확장성의 근거: 시설 식별·위치·관측·규칙을 같은 등록 형식으로 연결한다. 구동 조건은 ① 하천 영향을 받는 유형 ② 내수 배수 영향을 받는 유형으로 나누되 실제 유입 경로·유역/배수구역·현장 계측을 확인해야 한다. 가까운 수위/강우 관측소라는 이유만으로 대표성이 보장되지 않으며 오송의 임계 수치를 다른 시설에 복사하지 않는다. 후보 목록 확보와 운영 등록은 구분한다([자료 조사](docs/UNDERPASS_EXPANSION.md)).
- 공식 통제 기준(2026-10-10 확인, 원문 확보 필요): 행안부는 오송 이후 지하차도 차량 통제 기준을 침수심 15 cm에서 5 cm로 낮췄고(2026-05 보도), 진입차단시설 설치 대상 564곳 중 512곳 완료(2026-07 보도). 트윈은 침수심을 측정하지 않으므로 "침수심 5 cm 도달 전 선행 지표(수위·강우)로 몇 분 남았나"를 보여주는 보조 판단 도구로 정의한다. 통제 결정은 담당자·현장 기준이 우선한다.
- 지하차도 목록 자료(공공데이터포털): 국토교통부 「시설물안전법 대상 지하차도 현황」(CSV, 2023-09-30), 전국도로터널정보표준데이터(API), 서울시설공단·인천·부산 지하차도 현황. 침수 위험 등급 목록은 공개본 미확인.

확정 필요(사용자):
- [ ] 첫 시설을 궁평2지하차도(오송)로 두고 충북 지하차도 2~3곳을 더하는 안으로 갈지, 다른 사례(예: 서울 도시형 지하차도)로 시작할지. 자료 깊이는 오송이 가장 크다(수위·강우 10분, DEM, 사건 7단계).
- [ ] 발표자료 재구성 시점: 위 확정과 Phase 3 보드 화면이 생긴 뒤 심사항목(기획성 15·완성도 25·확장성 25·유용성 25·발표 10) 순서로 다시 만든다. 그 전에는 v3를 유지한다.

Phase 2 물리 모형 (PROJECT_PLAN Phase 2, 범위를 제한해 진행):
- [ ] LISFLOOD-FP(공개 소스) 실행 환경 확보. Windows 빌드 또는 Docker. HEC-RAS는 GUI 의존이 커 후순위.
- [ ] 입력: Copernicus DEM(기존), 미호강 수위 10분(기존), 임시제방 위치·높이(언론: 기존 제방 31.3 m·임시제방 29.7 m, 서로 어긋남·판결문 원문 필요), 붕괴 폭(미확보).
- [ ] 붕괴 유량은 위어 공식(월류 수두 = 관측 수위 − 제방고)으로 가정해 계산하고 가정값·민감도(제방고 ±0.5 m, 붕괴 폭 50/100/150 m)를 함께 표시한다. 물리 결과는 `SIMULATED`로 분류하고 공식 침수범위·침수심이 아님을 명시한다.
- [ ] 검증: Safemap 침수흔적 WMS 래스터와 시각 비교, 궁평2지하차도 도달 시각이 08:27 전후인지 확인. 공식 벡터 범위가 오기 전까지 "가정 민감도" 이상으로 주장하지 않는다.
- 블로커: 붕괴 위치·폭·시각 원문. 확보 전에는 가정 민감도 실험으로만 진행한다.

Phase 2.5 수위 상승 예측 (water-level-rise 방법을 실명 관측으로):
- [x] 대회 자료 사용 가능성 검토(2026-10-10): 익명 관측소·합성 시각·재식별 금지라 관측으로 쓰지 않는다. 특징 설계·검증 절차·코드만 재사용한다(`docs/WATER_LEVEL_INTEGRATION.md`, 다른 도구 작업).
- [x] 원출처 확보 경로(2026-10-10): `data/scripts/collect_hrfco_history.py`로 홍수통제소 OpenAPI 전국 목록(수위 1,420·강우 744)과 미호강 수위 3곳·강우 4곳의 2019~2026 1H·홍수기 10M 이력 확보. `docs/HRFCO_HISTORY.md`.
- [x] 전국 수집(2026-10-10): 홍수예보 지점 223곳 수위 + 가장 가까운 강우계 188곳의 2019~2026 1H 자료(약 3,300회 호출). `events` 집계: 관심 2,664·주의보 523·경보 179·계획홍수위 51건(224곳). 계획홍수위 있는 나머지 754곳은 필요할 때 같은 명령으로 받는다.
- [~] 품질 규칙(2026-10-10): 학습 스크립트가 1시간 3 m 초과 급변의 앞뒤 값을 버리고 정시 입력 없는 행을 만들지 않는다. 무자료 강우계는 후보 3곳 중 값이 있는 곳으로 자동 대체. 남은 것: catalog에 무자료·교체 관측소 표시, `events`에도 급변 제외 적용.
  - [x] 별도 품질 감사·격리 마스크(2026-10-10): `audit_hrfco_quality.py`로 미호강 3곳 확인. 각 46시간 누락, 미호강교 연구 격리 관측 12개가 입력·미래 정답 창 42개에 영향을 줌. 급변은 검토 표시, 명시적 격리·누락·중복·비유한 값은 학습 불가 표시. `hrfco-quality-policy.json`·`hrfco-quality.json`에 정책·SHA-256·옥산 무자료/관측소 교체 후보 메모. [구성과 발전 방향](docs/WATER_LEVEL_BUILDUP.md).
  - [x] 품질 마스크를 학습에 적용하고 재학습(2026-10-10, 대조 2026-10-12): 224곳 감사, 3,049,672행(−13). 마스크가 더 뺀 창은 미호강교 격리 12개, 3 m 급변 규칙이 20곳 40개 계단 주변 545개를 마스크보다 더 뺀다. 계단 원출처 확인 전까지 두 규칙 병행. [대조표](docs/RISE_MODEL.md#품질-마스크).
  - [ ] `events` 집계에도 품질 마스크 적용(`training_integration_complete=false`의 남은 이유), 급변 계단 40개 원출처 확인.
  - [ ] 2020·2024년 1월 1일 00:00~22:00의 수집 공백을 요청·응답과 대조해 보완한다. 공식 센서/기준면 오류 확인과 강우계 교체 확인도 필요.
    - 2026-10-12: 미호강교 연중 10분 자료에는 이 시간들의 값이 있다(1시간 자료에는 행 자체가 없음). 1시간 연 단위 요청의 응답 문제로 보이며, 10분 자료가 없는 나머지 221곳은 1시간 요청을 나눠 다시 받아 확인해야 한다.
- [x] 재학습·검증·카드(2026-10-10): `train_rise_model.py`로 224곳 305만 행 LightGBM 재학습(월 GroupKFold, 2023-07 제외). CV RMSE 0.181 m(외삽 0.440), 홀드아웃 계획홍수위 도달 적중 27/69·오경보 25(외삽 34/69·오경보 471). 오송 2023-07-15 계획홍수위 180분 전·경보 120분 전 «6시간 안 도달». `rise-forecast` API와 보드 연구 카드(권고와 분리). `docs/RISE_MODEL.md`.
  - [x] 90% 분위 상한 모델(2026-10-10, 기록 2026-10-12): 홀드아웃 계획홍수위 적중 43/69·오경보 254(중앙 27/69·25, 외삽 34/69·471), 상한 포함률 85.7%. 오송 계획홍수위 상한 240분 전, 보드 재생 04:10 상한 10.52 m. API `maxrise_6h_q90_m`·`reaches_within_6h_q90`, 연구 카드에 상한 KPI.
  - [ ] 남은 것: 오송 01:00~03:00 실제 상승(+3.0 m)이 상한(+1.4~2.8 m)도 넘음 → 사건 가중·분위 보정 검토, 실시간 강우 어댑터(실시간 모드에서는 과거 `at`도 강우 결측).
- [~] 전국 지하차도 좌표(2026-10-10): 도로터널 표준데이터에는 지하차도가 없어(사용자 확인) OSM 이름 매칭으로 282/938건에 좌표를 붙였다(`match_underpasses_osm.py`). 5 km 안 수위 관측소 228곳·홍수예보 지점 47곳(`link_facilities_to_gauges.py`). 남은 것: 미매칭 652건(지자체 CSV 주소 지오코딩·OSM 보완), 가까운 관측소가 실제 유입 하천인지 시설별 확인.

Phase 3 운영 트윈 (PROJECT_PLAN Phase 3, 앞당겨 진행):
- [~] 실시간 관측 어댑터(2026-10-10): `backend/app/twin.py`. 홍수통제소 10분 수위는 `HRFCO_API_KEY`로 live, 없으면 2023년 CSV `replay`. 10분 자료가 빈 값이면 1시간 자료로 대체한다(미호강교는 최근 10분 값이 수십 분 늦게 채워지는 것을 확인). 2026-10-10 03:10 실측 1.35 m·정상·계획홍수위까지 8.03 m 여유. 기상청 AWS는 `KMA_API_HUB_KEY` 발급 뒤 연결.
- [~] 시설 레지스트리(2026-10-10): `twin.py`의 `FACILITIES`에 궁평2지하차도 등록(미호강교 3011665, 관심 5.0·주의보 7.0·경보 8.0·계획홍수위 9.38 m). 충북 2~3곳 추가와 내수 침수형 유형은 남음.
- [x] 확장용 공식 지하차도 목록 확보(2026-10-10): 전국 시설물안전법 대상 938행·인천 42행·부산 59행·부천 14행 CSV 원본, 전체 출처 행 1,053개와 충북 후보 32행을 정리했다. 출처 간 중복 미통합이며 고유 시설 수/전국 전체 수가 아니다. 좌표·관측소·센서·통제 이력은 미확보, 운영 시설 추가는 0곳. `data/processed/facilities/`·`data/manifests/underpass-catalog.json`·[조사 결과](docs/UNDERPASS_EXPANSION.md).
- [ ] 후보 시설 2~3곳의 위치·관리기관·유입 경로·대표 관측·현장 계측·통제 이력을 확인하고, 시설별 규칙과 과거 사건을 대조한 뒤 운영 레지스트리에 등록한다.
- [x] 단계 판정 규칙 `river_stage_v1`과 백테스트(2026-10-10): 계획홍수위 도달 또는 경보 수위+60분 이내 도달이면 `CLOSURE_REVIEW`. 2023년 계열에서 06:50 이전 첫 권고, 유입까지 97분 이상·제방 붕괴까지 79분 이상(`test_twin.py`). `GET /api/twin/facilities/{id}/backtest`.
- [x] 지금 상태 보드 화면(2026-10-10): `#twin`(`src/dark/TwinBoard.tsx`). 상단을 실제 탭 3개(지금 상태·통제 기준 검토·백테스트)로 바꿨다. 지금 상태에 HAND 공간 상태 지도(`TwinSpatial.tsx`, 재생 시각까지 진행된 사건 단계, 실시간 모드는 범위 미표시)를 넣었고, 백테스트 탭에 2023 단계 전이와 사건 재생·검증 사례 링크를 모았다. 소개 화면은 «이 지하차도, 지금 막아야 할까» 서사와 보드 우선 버튼으로 교체.
- [x] 통제 기준 검토(2026-10-10): `GET /api/twin/facilities/{id}/criteria-review?stage_floor=&lead_threshold_min=`. 미호강교 2019~2026 10분 수위(2026-10-12부터 연중 409,152행 `miho_3011665_10m_2019_2026.csv.gz`, 이전 홍수기 140,544행, 2023 사건 433행 일치)에 같은 규칙을 적용해 2023 선행 시간과 다른 해 권고 구간을 함께 낸다. 현재 규칙(경보+60분) 05:50·유입 157분 전·다른 해 0건, 계획홍수위만 06:50·97분, 경보+120분 04:40·227분·2025-07-17 1건(40분, 최고 8.50 m). 다른 해 구간은 침수·통제 기록 미확인이라 오경보로 단정하지 않는다.
  - [ ] 2025-07-17 궁평2지하차도 통제·침수 여부 확인(충북도로관리사업소·보도). 확인되면 "불필요한 통제"인지 "필요했던 통제"인지로 표기를 바꾼다.
  - [x] 10분 자료 품질 표시와 10~5월 확장(2026-10-12): 연중 10분 수위 409,152칸, 빠진 칸 0·10분 0.3 m 이상 변화 13건(검토 표시만). 연중으로 넓히자 2023-05-16 계단 오류(1.51→11.26 m, 최고 13.28 m)가 모든 기준에 가짜 «계획홍수위 도달» 구간(11시간)을 만들어, 품질 정책의 연구 격리(01:00~12:00, 67개 값)를 규칙에서 뺀다. 그 뒤 8개 기준 결과는 홍수기만 쓸 때와 같고 10~5월 권고는 0건. API `quality`, 구간별 `quality_review_required`, 이미지에 `hrfco-quality-policy.json` 포함.
- [x] `water-level-rise` 입력·연구 근거 연결(2026-10-10): 실명 수위 0·1·3·6·12·24h 입력 6종, `forecast-readiness` API와 보드 이력 카드. 원본 749,657행 OOF를 재계산해 전체 0.221564 m·1m 초과 상승 구간 1.099863 m 오차를 확인했다. 시설 성능과 구분하고 예측값은 반환하지 않는다. [연결 범위](docs/WATER_LEVEL_INTEGRATION.md).
- [ ] 실제 시설 수위 예측: 기본 22종 중 나머지 강우·레이더·유역 입력 16종의 단위·대표성 확인, 익명 관측소별 통계의 재학습/제거, 실명·실제 시각 데이터로 사건 분리 검증. 원본 관측소·시각의 재식별 없이 진행하며, 검증 전에는 통제 판단에 적용하지 않는다.
- [x] 시설 Agent 세 도구 연결(2026-10-10): `get_facility_status`·`get_control_rule`·`get_facility_backtest`. 오송 상단 Agent의 "분석 범위 → 시설 통제 판단"에서 시설·과거 재생 시각을 선택한다. 시설 범위에서 기존 사건 분석 도구는 호출할 수 없으며 화면에서 고른 시설·시각을 서버가 고정한다. 기존 사건 분석은 별도 범위로 유지한다.
  - 실시간/과거 재생·관측 시각·신선도·규칙 가정·DQ-009 차이를 구분한다. 관측 누락·지연 시 `NEEDS_DATA`, 실시간 오류를 과거 자료로 대체하지 않는다.
  - offline 시설 질문 3/3, 실제 Gemini 시설 질문 3/3 모델 설명 완료(HTTP 6회, 관측은 2023년 재생). 사용법·한계는 [docs/FACILITY_AGENT.md](docs/FACILITY_AGENT.md).
  - 전체 백엔드 178개·프런트엔드 7개·E2E 11개·빌드 통과. 이후 UTC `Z` 케이스를 추가한 시설 테스트 19개도 통과했다.
- [ ] 공개 서버 재배포(완성도 항목). 배포 전 `docs/DEPLOY_AWS.md` 체크리스트.
- [ ] PROJECT_PLAN.md의 Definition·Phase 절을 이 방향으로 갱신한다.

## NOW

- Status: Active / 시설 중심 운영 트윈으로 전환 중
- Last updated: 2026-10-10
- Branch: 모든 작업은 `main` 하나에서 진행한다. 2026-09-06에 브랜치 4개를 `main`으로 정리했다.
- Next action: 지금 상태 보드와 통제 기준 검토·백테스트 탭을 구성하고, 관측 신선도·담당자 판단 경계를 화면 전체에 맞춘다. 시설 확장 대상 확인과 실무 인터뷰·파일럿, 공식 통제 원문 확보를 이어간다.

- [x] Agent 연결 안정화 1차 (2026-10-09)
  - `/api/agent/ask`의 모델 단계·JSON 재시도가 전체 `AGENT_ASK_TIMEOUT_SECONDS`(기본 25초)를 공유한다. 남은 시간에 HTTP 요청을 취소하고 도구 결과 폴백을 유지한다. 로컬 분석·직렬화 시간은 추가될 수 있다.
  - 응답 `diagnostics`에 요청 ID·소요 시간·모델 단계/HTTP 시도 수·완료 경로·실패 단계/코드를 추가했다. 모델·입력 검증·도구 실행·답변 근거 오류를 구분한다.
  - 질문 1,000자·대화 6개·각 대화 1,500자 제한을 UI/API에 맞췄다. 긴 답변 후 후속 질문의 422를 예방하고 사건 전환 시 이전 요청·답변을 버린다.
  - 1차 당시 백엔드 128개·프런트엔드 7개·Playwright E2E 5개와 빌드 통과. 아래 후속 대화 보완에서 검증 범위를 확대했다.
- [x] Agent 후속 대화·실행 입력 대조 (2026-10-09)
  - 명시적 후속 질문만 직전 사용자 조건을 이어받으며, 같은 분석의 새 수치는 기존 값을 교체한다. Assistant 숫자·중간에 바뀐 주제·모호한 상대 시간·복합 조건은 임의로 합치지 않는다.
  - 모델 입력 검증은 전체 과거 숫자 대신 서버가 선택한 `parameter_context`를 사용한다. 호출 기록도 정규화 후 실제 입력을 표시한다.
  - `context_note`와 `diagnostics.context_mode`로 이번 질문·재사용·조건 변경·확인 필요를 구분한다.
  - 백엔드 150개·프런트엔드 7개·E2E 10개 통과, 프로덕션 빌드 통과. 브라우저→실제 로컬 Agent API의 08:20→재사용→08:10 흐름도 확인했다.
  - `backend/evaluation/evaluate_agent.py`와 13개 질문으로 Agent/직접 분석 API를 재대조할 수 있다. offline 13/13 통과(도구 11·조건 확인 2, 모델 요청 0).
- [ ] 실제 Agent 종단 간 대조
  - [x] 오송 소수 질문 4건 점검: 모델 설명 3건·조건 확인 1건, 실제 모델 HTTP 6회. 08:20의 7분, 재사용 7분, 08:10의 17분이 직접 분석과 일치했다.
  - [docs/AGENT_EVALUATION_RESULTS.md](docs/AGENT_EVALUATION_RESULTS.md)에 질문·완료 경로·소요 시간·한계를 기록했다. 공개 서버 배포 검증이나 전체 성공률 측정은 아니다.
  - [ ] 서울·포항·안동의 실제 모델 대조, 물리 효과 질문, 장시간·동시 사용 확인.
  - [docs/AGENT_VALIDATION.md](docs/AGENT_VALIDATION.md)의 사건별 질문·후속 대화·실패 경로를 실제 Gemini와 직접 분석 API로 대조한다.
  - 모델 설명 완료와 도구 폴백을 구분해 측정한다. planner-status 가용성이나 HTTP 200만으로 실제 연결 완료로 판단하지 않는다.
- [x] 시장성·유용성 검증 실행 양식 준비 (2026-10-09)
  - [docs/MARKET_VALIDATION.md](docs/MARKET_VALIDATION.md)에 사용자/도입 검토자 가설, 교류회에서 얻을 도움, 20분 인터뷰, 5~8명 대조 파일럿 과제·평가·진행 조건을 구체화했다.
  - `docs/market-validation/`에 인터뷰·파일럿 기록 CSV 헤더를 준비했다. 실제 참여·답변·구매 의향·매출 기록은 아직 없다.
- [ ] 교류회 후 시장 인터뷰·파일럿 수행
  - 반복 업무·현재 대안·구매 검토 주체·도입 조건을 기록하고, 기존 방식과 FloodOps의 완료·오류·시간을 대조한다.
  - V1·V2 PPT는 보존하며 실제 결과 확보 후 유용성·시장 근거 장표를 갱신한다.

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
  - 현재 기본 모델: 코드의 `gemini-3.5-flash-lite`(`GEMINI_MODEL`로 변경), 자격증명 `GEMINI_API_KEY`. 키 미설정 시 결정론 planner·등록 도구 폴백을 사용한다. `/ask` 모델 전체 예산은 위 Agent 안정화 항목을 따른다.
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
  - 서울 Agent는 아래 2026-10-03 다중 사례 확장에서 경보 시점·저류 비교를 지원한다. 반경 재고(`exposure-inventory`)는 서울에서 404를 유지한다.
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
  - 세 사례 모두 안동 규칙(하천 양안 띠, 거리 = 비율²×2 km)으로 통일(2026-10-10 저녁). 서울 띠 405 → 1,218(강우 비율) + 공식 흔적 0 → 1,557 → 10,468건, 포항 띠 0·0·236·370·403·415, 안동 띠 605·952·973·1,035·1,073·788·265. 서울 띠는 흔적 대조 14~16%라 도식으로만 표시.
  - 남은 것: 포항·안동에 관측 강우·수위가 연결되면 보도 순서 임계를 관측 기반으로 교체. 구계리는 재현 안 됨.
- [x] 최종발표 자료 v3 (2026-10-10): BASEMENT 2차 발표자료와 같은 도구로 24장 재구성. `docs/presentations/FloodOps-2026-v3/`, 권장 발표 730초. 발표 날짜(표지 «2026. 12.»)와 팀·발표자 표기는 확정 뒤 수정.
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

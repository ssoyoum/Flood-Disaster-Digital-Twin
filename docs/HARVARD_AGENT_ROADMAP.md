# FloodOps — Harvard CS2680 관점의 Agent 실행 계획

## 목적
FloodOps를 근거 추적이 가능하고 반복 측정할 수 있는 홍수 대응 의사결정 지원 Agent로 발전시킨다. Harvard CS2680의 다섯 축인 Mads-Lens(관찰), Mads-Loop(실행 루프), Mads-Opt(비용·지연 최적화), Mads-Serve(모델 서빙), Mads-Stack(전체 스택 최적화)를 프로젝트에 맞게 적용한다.

## 현재 구조와 원칙
FloodOps는 Gemini 기반 Agent가 사건·시설 범위마다 등록된 읽기 전용 도구 중 필요한 도구를 선택하고, 모델 판단 최대 6회·성공 도구 호출 최대 4회·요청당 25초 안에서 루프를 돈다. 서버는 도구명과 인자를 검증하며 답변에 근거와 호출 내역을 제공한다.

### 코드 위치와 도구 (2026-10-15 확인)
- 루프: `backend/app/agent_runner.py`의 `ask_agent` → `_ask_agent`(라우팅 → 모델 판단 → `_validated_tool_request` → `execute_agent_tool` → `_grounded_answer` → `_reply`). 모델 호출은 `_gemini_action`.
- 질문 조건 해석: `backend/app/agent_context.py`(`resolve_question`), 추천 도구: `_router_hints`·`agent_cases.hints`·`agent_facility.hints`.
- 도구 카탈로그: 오송 `agent_tools.py`, 서울·포항·안동 `agent_cases.py`, 시설 `agent_facility.py`.
- 별도 경로: `/api/agent/plan`의 `llm_planner.py`는 워크플로 하나만 고르는 라우터이고 이 루프와 다르다.

| 범위 | 도구 수 | 도구 |
|---|---|---|
| 오송 2023 | 8 | get_event, get_reconstruction, get_observation_summary, analyze_closure_timing, analyze_inflow_delay, get_exposure_inventory, compare_scenarios, analyze_hand_threshold |
| 서울 2022 | 5 | get_event, get_reconstruction, get_observation_summary, analyze_alert_timing, analyze_storage_capture |
| 포항 2022 · 안동·의성 2026 | 4 | get_event, get_reconstruction, get_observation_summary, analyze_response_timing |
| 시설(궁평2) | 3 | get_facility_status, get_control_rule, get_facility_backtest |

고유 도구 이름은 14개다. 처음 이 문서와 README에 적힌 "7개"는 현재 코드와 맞지 않아 고쳤다.

- 분석값은 도메인 도구가 계산한다. 모델은 값을 지어내지 않고 선택·해석·설명한다.
- 도구는 읽기 전용으로 유지한다.
- 공식 관측, 출처 기반 정보, 근사 재구성, 가정 시나리오를 명확히 구분한다.
- 근거가 부족하면 추측하지 않고 불확실성과 한계를 밝힌다.
- 도구를 늘리기 전에 현재 도구의 정확성, 실패 처리, 지연과 비용을 측정한다.

## 우선순위
| 우선순위 | 할 일 | 산출물 | 완료 조건 |
|---|---|---|---|
| P0 | Agent 실행 전 과정 계측 | 요청별 trace | 질문부터 최종 답변까지 재구성 가능 |
| P0 | 고정 평가 질문 세트 | 30개 이상 benchmark | 동일 조건으로 회귀 평가 가능 |
| P1 | 도구 계약과 실패 정책 명시 | 입출력·오류 명세 | 잘못된 인자, 빈 결과, 타임아웃이 안전하게 처리됨 |
| P1 | 품질·비용 기준선 확보 | JSONL/CSV 결과 | 품질과 지연을 같은 질문으로 비교 |
| P2 | 모델 대안 비교 | 비교 실험 보고서 | 데이터에 근거해 전환 여부 결정 |
| P2 | 전체 경로 프로파일링 | 병목 보고서 | API·도구·LLM·UI 병목을 구분 |

## Stage 1 — Mads-Lens: 관찰 가능성
- [x] 요청별 trace ID를 만든다. (`diagnostics.request_id`, 2026-10-09)
- [x] 질문 → 모델 요청 → 선택 도구/인자 → 서버 검증 → 도구 실행 → 도구 결과 → 후속 모델 요청 → 최종 답변을 하나의 trace로 연결한다. (`diagnostics.trace`, 2026-10-15)
- [x] 단계별 소요 시간, 도구명, 검증 결과, 오류 유형, 입력·출력 토큰(제공되는 경우)을 기록한다. (`trace[].ms`, `diagnostics.tokens`)
- [x] 로그에는 결과 요약과 근거 ID를 남기고, 원본 데이터 전체를 무조건 복제하지 않는다. (`FLOODOPS_AGENT_TRACE_LOG` JSONL, 질문·파라미터·도구 결과 제외)
- [x] UI의 도구 호출 이력과 서버 로그가 일치하는지 확인한다. (API 응답과 JSONL 줄의 request_id·trace·도구 순서 일치를 테스트로 확인. 브라우저 화면 대조는 아직)
- [~] 도구 선택 오류, 인자 오류, 빈 결과, 예외/타임아웃, 근거 부족을 별도 분류한다. (선택·인자·반복 호출·실행 실패·모델 시간 초과·근거 부족은 분리. 빈 결과는 도구별 정의가 없어 아직 분류하지 않음)

완료 기준: trace 하나만 보고 어떤 도구가 왜 호출됐고 무엇을 반환했으며 답변이 어떤 근거에 기대는지 설명할 수 있다.

## Stage 2 — Mads-Loop: 실행 루프와 실패 정책
- [x] 14개 도구의 목적, 입력 스키마, 출력 스키마, 데이터 전제조건을 표로 정리한다. ([AGENT_TOOL_CONTRACTS.md](AGENT_TOOL_CONTRACTS.md))
- [x] 루프 상태와 종료 조건을 명시한다: 모델 요청, 도구 검증, 도구 실행, 추가 호출 또는 최종 응답, 완료/실패. (같은 문서 "루프 상태와 종료 조건")
- [x] 최대 도구 호출 수, 전체 시간 제한, 반복적인 잘못된 호출, 모델 오류의 종료 정책을 테스트한다. (`test_agent_budget.py`, `test_agent_stability.py`: 실패 호출 재요청 즉시 종료, 성공 호출 반복 2회 종료)
- [x] 입력 검증 실패와 도구 실행 실패를 구분한다.
- [x] 빈 결과와 자료 미확보는 정상적인 상태로 표현하며 임의의 수치로 채우지 않는다. (도구 실패 3문항 live에서 숫자 없는 `NEEDS_DATA`)
- [x] 재시도는 일시적 오류에만 제한하고, 잘못된 인자나 근거 부족을 무한 재시도하지 않는다. (JSON 형식 오류 1회만 재시도)
- [~] 각 도구에 timeout과 전체 요청 deadline을 둔다. (요청 전체 25초만. 도구는 로컬 계산이라 개별 제한 없음)
- [x] 사용자에게 내부 stack trace 대신 이해 가능한 오류와 다음 행동을 안내한다.

### Benchmark 질문 유형
1. 정상 분석: 등록된 사례의 시점 또는 시나리오 비교
2. 도구 선택: 질문에 맞는 도구 선택
3. 모호한 질문: 사례·기준 시각이 불명확할 때 확인 또는 한계 설명
4. 자료 부족: 공식 침수범위·관측값이 없을 때 가능한 판단과 불가능한 판단 구분
5. 잘못된 입력: 미등록 사례 ID, 범위 밖 숫자, 잘못된 인자 거부
6. 도구 실패: 예외·빈 결과 이후 수치 환각 방지
7. 안전한 표현: 근사 HAND 셀·시설 재고·가정 시나리오를 실제 피해량이나 검증된 예측이라고 부르지 않기

각 테스트는 질문, 사례 ID, 기대 도구/행동, 필수 근거, 금지 주장, 기대 상태를 저장한다. 최소 30개로 시작한다.

→ 2026-10-15: `backend/evaluation/agent_benchmark_cases.json` 39문항, 실행기 `agent_benchmark.py`. 사용법은 [AGENT_VALIDATION.md](AGENT_VALIDATION.md#고정-벤치마크-2026-10-15), 기준선은 [AGENT_EVALUATION_RESULTS.md](AGENT_EVALUATION_RESULTS.md).

## Stage 3 — Mads-Opt: 품질을 유지하며 비용·지연 개선
- [ ] 평가 질문, 모델 버전, 프롬프트 버전, 데이터 버전을 고정한다.
- [ ] 요청당 LLM 호출 수, 도구 호출 수, 토큰, p50/p95 지연, 성공률을 기록한다.
- [ ] 중복 도구 설명과 컨텍스트를 줄이되 단위·전제조건·자료 한계는 유지한다.
- [ ] 이미 확정된 사례/화면 정보가 중복 전달되는지 확인한다.
- [ ] 의존성이 없는 읽기 전용 도구만 병렬화 후보로 삼는다.
- [ ] 저렴한 모델 라우팅은 별도 실험으로 검증한다.
- [ ] 캐시는 사례, 질문, 도구 인자, 데이터·코드·프롬프트 버전을 반영해 오래된 결과가 재사용되지 않도록 한다.
- [ ] 최적화 전후 같은 benchmark를 돌리고 품질이 떨어지면 되돌린다.

측정 지표:
- Task success rate: 기대 분석 또는 적절한 한계 설명을 완수한 비율
- Evidence validity: 답변 근거가 실제 도구 결과와 일치하는 비율
- Tool accuracy: 올바른 도구·인자를 사용한 비율
- Unsupported-claim rate: 근거 없는 수치·인과·예측 주장 비율
- 요청당 LLM/도구 호출 수와 토큰
- p50/p95 지연
- 성공 작업 1건당 추정 비용

## Stage 4 — Mads-Serve: 모델 서빙 판단
GPU 자체 서빙을 먼저 만들지 않는다. 도메인 도구와 자료의 신뢰성이 우선이다.
- [ ] 현재 Gemini 구성을 기준선으로 고정한다.
- [ ] 대체 모델은 동일 질문 세트와 동일 도구 계약으로 비교한다.
- [ ] 한국어 도메인 설명, 도구 호출 JSON 유효성, 근거 보존, 지연, 총 운영비를 함께 측정한다.
- [ ] 자체 서빙 비용에 GPU 유휴 시간, 배포, 모니터링, 장애 대응을 포함한다.
- [ ] 품질 기준을 충족하지 못하면 전환하지 않는다.

산출물은 우선 자체 서빙 구현이 아니라 모델 전환 판단 보고서다.

## Stage 5 — Mads-Stack: 전체 경로 최적화
- [ ] 브라우저 → API → Agent loop → 도구 → Gemini → 검증 → UI의 시간을 분해한다.
- [ ] 병목이 모델 대기인지, 도구/자료 로딩인지, 직렬화나 지도 렌더링인지 확인한다.
- [ ] 변경 전 검증 가능한 가설을 한 문장으로 작성한다.
- [ ] 한 번에 주요 변수 하나만 바꾸고 동일 benchmark를 재실행한다.
- [ ] 성능뿐 아니라 근거성, 도구 정확성, 실패 사례도 기록한다.

## 4주 실행안
### 1주차: 관찰과 기준선
- [x] 도구와 실제 루프 코드 위치 확인 (위 "코드 위치와 도구")
- [x] 최소 trace 및 지표 구현
- [x] 실제 질문 30개 이상 benchmark 작성 (39문항)
- [x] 기준선 결과와 알려진 한계를 커밋 (2026-10-15, [평가 기록](AGENT_EVALUATION_RESULTS.md))

### 2주차: 안정성
- [x] 입출력 계약, 종료 조건, timeout, 오류 분류 문서화 ([AGENT_TOOL_CONTRACTS.md](AGENT_TOOL_CONTRACTS.md))
- [x] 정상·모호·자료 부족·도구 오류 테스트 자동화 (벤치마크 offline은 모델 없이 매번 돌릴 수 있음)
- [x] 근거 없는 수치 생성 방지 회귀 테스트 추가 (천 단위 표기는 통과, 지어낸 값은 거부)

### 3주차: 최적화
- [ ] 토큰·호출 수·p50/p95 기준선 측정 (지연은 Gemini 응답 속도가 실행마다 3배까지 달라, 같은 시간대에 3회 이상 반복해 비교)
- [ ] 프롬프트, 도구 설명, 컨텍스트 중 한 변수씩 실험
- [ ] 품질을 유지한 변경만 채택

### 4주차: 전체 경로 보고
- [ ] 프런트/API/도구/LLM 지연 분해
- [ ] 가설·조건·결과·실패 사례를 재현 가능한 보고서로 작성

## 완료 정의
- [ ] 전체 요청 trace 확인 가능
- [ ] 30개 이상 질문으로 회귀 평가 가능
- [ ] 근거 유효성, 도구 정확성, unsupported-claim rate 측정
- [ ] 최적화 전후 품질·비용·지연 비교
- [ ] 자료 부족 상황에서 추측성 수치를 만들지 않음
- [ ] 결과와 한계를 Markdown으로 기록

## 지금 하지 않을 일
- 평가 없이 도구 수 늘리기
- 실제 예측 모델이 아닌데 예측 모델처럼 포장하기
- 근거 없는 침수범위·피해액 생성하기
- 측정 전에 멀티 에이전트 도입하기
- 기준선 없이 GPU 자체 서빙으로 전환하기

## 참고 자료
- [Harvard CS2680 개요](https://cs2680.seas.harvard.edu/)
- [Harvard CS2680 과제](https://cs2680.seas.harvard.edu/assignments/)
- [Harvard CS2680 프로젝트](https://cs2680.seas.harvard.edu/project)
- [FloodOps README](../README.md)
- [FloodOps Architecture](ARCHITECTURE.md)

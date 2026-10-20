# Agent 도구 계약과 실패 정책

작성일: 2026-10-15. [Harvard 로드맵](HARVARD_AGENT_ROADMAP.md) Stage 2의 "도구 입출력·종료 조건·오류 분류" 문서다. 도구 설명(`use_when`·`can_say`·`cannot_say`)의 원본은 코드의 카탈로그이며 모델도 같은 문장을 받는다: 오송 `backend/app/agent_tools.py`, 서울·포항·안동 `backend/app/agent_cases.py`, 시설 `backend/app/agent_facility.py`. 이 문서는 그 위에 서버가 실제로 강제하는 규칙을 정리한다.

## 범위별 도구

모든 도구는 읽기 전용이다. `event_id`·`facility_id`·`observation_at`은 화면에서 고른 값으로 서버가 고정하며, 모델이 바꾸면 `tool_input_rejected`다.

| 도구 | 범위 | 모델이 줄 수 있는 입력 | 서버 검증 | 출력 | 말할 수 없는 것 |
|---|---|---|---|---|---|
| get_event | 4개 사건 | 없음 | — | 사건 메타데이터·자료 상태 | 시각별 수치 |
| get_reconstruction | 4개 사건 | 없음 | — | 단계별 시각·출처·확신도 | 시각을 바꾼 결과, 피해 |
| get_observation_summary | 4개 사건 | 없음 | — | 오송: 강우·수위 최대값 / 서울: 강우계·침수흔적 집계 / 포항·안동: 보도 수치와 출처 | 예보, 보도에 없는 수치 |
| analyze_closure_timing | 오송 | `closure_times` | 1~10개, 각 값이 질문의 HH:MM, 이번 요청의 `get_reconstruction` 단계 시각, 또는 기준 통제 08:27에서 계산한 "N분 일찍/늦게" 시각 | 통제 시각별 유입·주행불능·완전침수까지 분 | 차량·사상자·침수심 감소 |
| analyze_inflow_delay | 오송 | `delay_minutes` | 1~10개 정수, 각 값이 질문에 "N분"으로 적힘, 0~180 | 단계 시각 이동 | 차수벽·펌프의 실제 지연 효과 |
| analyze_breach_advance | 오송 | `advance_minutes` | 1~10개 정수, 각 값이 질문에 "N분"으로 적힘, 앞선 월류 07:50 이후 순서를 보존하는 최대 18분 | 제방 붕괴와 후속 기록 시각의 동일 분 이동 | 붕괴·유량·침수·교통·피해의 물리 변화 |
| get_exposure_inventory | 오송 | `radii_m` | 1~10개 정수, 각 값이 질문에 적힘, 50~20,000 m | 반경별 건물·도로·시설 수 | 침수 건물 수·피해 |
| compare_scenarios | 오송 | `comparison_type` + `closure_times` 또는 `delay_minutes` | 종류와 맞는 값이 있어야 함, 값 규칙은 위와 같음 | 기준 대비 단계 시각 차 | 피해 감소량 |
| analyze_hand_threshold | 오송 | `reduction_m` | 질문에 "N m"로 적힌 0~2.5 값, 물리 시설 변경 질문이면 거부 | 단계별 HAND 셀 수 변화 | 제방·차수벽 효과, 실제 침수 범위 |
| analyze_alert_timing | 서울 | `thresholds_mm_per_hour`, `alert_times` | 하나 이상, mm 값은 질문에 적힌 값(0~200), 시각은 질문·단계 시각 | 경보 시각, 첫 구조 신고(20:59)까지 분 | 대피 인원, 인명 피해 감소 |
| analyze_storage_capture | 서울 | `storage_m3`, `capacity_mm_per_hour`, `runoff_coefficient` | 부피는 질문 값 또는 등록값 400,000·320,000, 처리능력은 질문 값 또는 95·100·110, 유출계수는 질문 값 | 초과 부피, 저류 비율, 가득 차는 시각, 첫 구조 신고 시각과 그 전 분 | 침수 면적·침수심·피해 감소 |
| analyze_response_timing | 포항·안동 | `intervention_id`, `action_times` | 등록된 대응 ID(포항 parking_entry_ban, 안동 evacuation_order·landslide_alert), 시각 1~10개는 질문·단계 시각·"N분 일찍" | 대응 시각이 이후 사건보다 앞서는 분 | 대피 성공, 인명·피해 감소 |
| get_facility_status | 시설 | 없음 | 시설 범위에서만 등록 | 관측 모드·시각·수위·단계·여유, 신선도(`fresh`/`stale`/`missing`) | 침수심, 예보, 실제 통제 명령, 오래된 관측으로 안전 보장 |
| get_control_rule | 시설 | 없음 | 〃 | 등록 수위·상승 속도 조건과 한계 | 미확인 법정 기준 확정, 통제 승인 |
| get_facility_backtest | 시설 | 없음 | 〃 | 첫 통제 검토 시각, 유입·붕괴까지 분, DQ-009, 보관 자료·현재 기준값 한계 | 실제 통제 기록, 피해 감소 |
| get_criteria_review | 시설 | 없음 | 〃 | 8개 기준(주의보·경보 × 0~180분)별 첫 검토·유입까지 분·다른 시기 권고 수, 연도별 최고 수위, 자료 품질, 보관 자료·현재 기준값 한계 | 다른 해 권고의 필요·불필요, 최적 기준 확정 |
| get_rise_forecast | 시설 | 없음 | 〃 | 연구 모델 6시간 최대 상승·예상 수위(중앙값, 있으면 90% 상한), 모델 오차, `kind=RESEARCH` | 예보·도달 시각·침수심, 통제 필요 판단 |

시설 범위에서는 시설 도구 5개만, 사건 범위에서는 그 사건의 도구만 등록된다(`list_agent_tools`). 범위 밖 도구를 고르면 `tool_selection_rejected`다.

## 자료 전제와 실패

도구가 필요한 처리 자료를 찾지 못하면 `ReconstructionUnavailable`을 내고 루프는 `tool_execution_failed`로 기록한다. 실시간 시설 관측은 실패해도 과거 자료로 대신하지 않으며, 키가 들어 있을 수 있는 원본 오류 문구를 돌려주지 않는다. 빈 결과(예: 반경 안 건물 0동, 백테스트에서 검토 조건 미도달)는 오류가 아니라 정상 결과이며, 도구가 그 상태를 문장이나 `null`로 돌려준다.

## 루프 상태와 종료 조건

`ask_agent` 한 요청의 흐름(`diagnostics.trace`에 같은 순서로 남는다):

1. **router** — 도움말 질문이면 모델 없이 답한다. 후속 질문의 조건이 모호하면 모델 없이 확인을 요청한다(`clarification`).
2. **model** — 모델이 도구 하나를 고르거나 최종 답을 낸다. JSON이 틀리면 1회만 다시 묻는다.
3. **validation → tool** — 위 표의 규칙을 통과한 호출만 실행한다.
4. **answer** — 인용 번호와 숫자가 도구 결과에 있는지 검사한다(`grounded`). 숫자는 결과 JSON 표기로 맞춰 본다(본문의 `1,242,453` = 결과의 `1242453`).
5. **reply** — 상태와 완료 경로(`completion_source`)를 정한다.

| 조건 | 동작 |
|---|---|
| 모델 판단 6회 | 루프 종료, 질문에 적힌 값의 추천 도구를 서버가 실행해 결과 반환 |
| 성공 도구 호출 4회 | 루프 종료, 같은 처리 |
| 요청 전체 25초(`AGENT_ASK_TIMEOUT_SECONDS`) | 새 모델 요청 없이 같은 처리 |
| 실패한 호출을 다시 요청 | 즉시 종료(재시도해도 성공할 수 없음). 그 도구는 서버 대체 실행에서도 뺀다 |
| 성공한 호출을 다시 요청 | 이전 결과 번호를 알려 주고 계속, 반복이 2번째면 종료 |
| 모델 장애 + 물리 시설 효과 질문 | 도구 없이 수리모형 부재를 설명하고 `NEEDS_DATA` |
| 모델 장애 + 예보 질문(내일·앞으로·예보 등) | 과거 관측을 대신 보여주지 않고 `NEEDS_DATA` |
| 모델 장애 + 그 밖의 질문 | 추천 도구 결과가 있으면 `ANSWERED`(`registered_tools`), 없으면 `UNAVAILABLE` |
| 가정 질문인데 계산 도구 없이 기록 시각만 인용 | 답변은 유지하되 `NEEDS_DATA`와 한계 문구 |

재시도는 모델 JSON 형식 오류 1회뿐이다. 잘못된 인자·근거 부족은 재시도하지 않고, 사용자에게는 내부 예외 대신 `limitations`와 `follow_ups`로 다음 질문을 안내한다.

## 오류 분류

`diagnostics.failures[].code`와 `trace[].outcome`에 같은 코드가 쓰인다. 표는 [AGENT_VALIDATION.md](AGENT_VALIDATION.md#응답에서-실패-위치-확인)에 있다: 모델(`model_unavailable`·`model_connection_failed`·`model_http_error`·`model_budget_exceeded`·`model_invalid_decision`), 검증(`tool_selection_rejected`·`tool_input_rejected`·`tool_call_repeated`), 도구(`tool_execution_failed`), 답변(`answer_not_grounded`).

## 남은 것

- 도구별 개별 시간 제한은 없다. 도구는 로컬 계산이고 요청 전체 예산만 적용된다. 첫 요청의 자료 적재(반경 재고 약 5 s)가 가장 길다.
- 이 표는 손으로 맞춘 것이다. 카탈로그나 검증 규칙이 바뀌면 함께 고쳐야 한다.

## 실행 경로와 근거 전달의 코드 연결 (2026-10-20 정적 검토)

기준: `ssoyoum/Flood-Disaster-Digital-Twin` 커밋 `88a7ee489d9f62ac4943dff8b86330a57aa6b72e`. 이번 확인은 코드 읽기이며 테스트·API·Live 모델은 실행하지 않았다. 실행 수명주기와 실패 목록을 이 문서에서 관리하므로 별도 AGENT_EXECUTION_LIFECYCLE / AGENT_FAILURE_CATALOG 문서를 만들지 않는다.

| 단계 | 실제 코드·함수 | 입력 → 출력 / 서버 경계 |
|---|---|---|
| HTTP 수신 | `backend/app/main.py:ask_agent_question`, `backend/app/schemas.py:AgentAskRequest` | POST /api/agent/ask. 사건·시설 범위와 rate limit을 확인한 뒤 ask_agent 호출. HTTP 입력 오류와 아래 업무 상태는 별개 |
| 요청 격리 | `backend/app/agent_runner.py:ask_agent`, `_RunState` | ContextVar에 deadline·trace·실패·토큰 집계를 요청별 보관하고 finally에서 reset |
| 질문 해석 | `backend/app/agent_context.py:resolve_question`, `agent_runner._ask_agent` | 사건 / 시설 / watch 라우터로 조건을 해석. 도움말은 capability, 모호한 후속 조건은 clarification으로 모델 호출 없이 종료 |
| 모델 입력 | `_model_catalogue`, `_system_prompt`, `_model_action` | 질문·최대 6개 history·고정 scope·허용 도구·기존 observations·남은 호출 수를 전달 |
| 모델 결정 | `_gemini_action` / `_ollama_action`, `AgentAction` | 구조화된 tool 또는 final 결정. JSON 검증 실패 시 1회 재요청. 모델이 도구를 고르는 것과 계산값을 산출하는 것을 분리 |
| 서버 검증 | `_validated_tool_request`, `AgentToolCallRequest` | 도구 등록·범위·허용 인자·사용자/기록에 실제 있는 시각·숫자를 검사. 시설·사건·관측 시각 변경 금지 |
| 실제 실행 | `backend/app/agent_tools.py:execute_agent_tool` | 등록 서비스 실행. 사건별 분기는 agent_cases, 시설은 agent_facility, watch는 agent_watch로 이어짐 |
| 모델에 결과 재전달 | `agent_runner._observation` | 성공 결과를 observations에 추가. get_reconstruction의 지도 표시 필드와 HAND grid ID는 모델 입력에서 제외. 원본 호출 결과는 응답·근거 대조에 유지 |
| 답변 검사 | `_grounded_answer`, `_numbers`, `_reply` | 인용 번호가 실제 호출 순번인지, 인용 표기와 답변 숫자가 인용 결과 JSON에 있는지 검사. 시설·watch의 추가 안전 표현은 각 도메인 처리 |
| 응답·기록 | `schemas.AgentAskResult`, `_write_trace_log` | status·answer·tool_calls·evidence_calls·limitations·diagnostics 반환. 선택적 trace 파일에는 질문·인자·결과 원문을 쓰지 않음 |

**plan 경로와 ask 루프를 혼동하지 않는다.** POST /api/agent/plan은 `main.plan_agent → llm_planner.plan_with_llm` 또는 `agent_tools.plan_agent_intent`로 실행하지 않는 계획을 만든다. /ask는 위 반복 루프다. plan의 workflow enum을 ask의 전체 도구 목록으로 쓰지 않는다.

### 시간 예산의 실제 보장 범위

- 모델 판단 최대 6회, 성공 도구 최대 4회. 성공 호출 중복은 기존 결과 참조 후 반복 시 종료하고, 실패 호출은 다시 계산하지 않도록 추적한다.
- Gemini 기본 25초 / Ollama 기본 300초의 요청 deadline을 모델 호출·JSON 재시도가 공유한다. `_post_gemini`의 asyncio.wait_for가 HTTP 작업 취소를 수행한다.
- **모든 동기 도구 실행을 강제로 중단하는 전체 요청 deadline은 아니다.** 도구·외부 자료 로딩이 오래 걸리면 요청 전체 지연이 모델 예산보다 길 수 있다. 이 위험의 별도 타임아웃·부하 검증은 미검증이다.

### 실패 카탈로그: 구현과 테스트 존재를 분리

다음 테스트는 파일·함수를 읽어 존재를 확인했으며 이번 실행 결과가 아니다. 동일 코드라도 확보한 도구 결과·질문 범위에 따라 상태가 달라지므로 실패 코드와 status를 일대일 대응시키지 않는다.

| 실패 / 자료 상태 | 탐지·진단 | 외부 응답과 현재 처리 | 근거 테스트 |
|---|---|---|---|
| 미등록 도구·범위 밖 선택 | validation / tool_selection_rejected | 호출 거절. 다른 도구를 선택하거나 서버 근거로 응답 / 근거가 없으면 보류 | `backend/tests/test_agent_budget.py:test_api_distinguishes_input_rejection_from_tool_failure_and_resets_state` |
| 사용자에게 없는 수치·인자·scope 변경 | validation / tool_input_rejected | 검증 실패 인자를 실행하지 않음 | `backend/tests/test_agent_facility.py:test_model_cannot_switch_facility_time_or_borrow_historical_tools` |
| 반복 호출 | validation / tool_call_repeated | 재실행을 막고 확보한 결과 / 자료 부족으로 종료 | `backend/tests/test_agent_stability.py:test_retrying_a_failed_tool_stops_the_loop` |
| 자료·분석 실행 실패 | tool / tool_execution_failed | 실패 분석을 모델이 시간표로 대신 계산하지 않음. 자료 부족 경로 | `backend/tests/test_agent_stability.py:test_failed_analysis_is_not_recomputed_by_the_model_from_the_timeline` |
| 모델 설정·연결·HTTP·JSON 실패 | model_unavailable / model_connection_failed / model_http_error / model_invalid_decision | 사용자 조건의 등록 도구를 서버가 실행할 수 있으면 registered_tools. 반환 근거도 없으면 UNAVAILABLE, 계산 불가 질문은 NEEDS_DATA 가능 | `backend/tests/test_agent_budget.py`, `backend/tests/test_agent_ollama.py` |
| 모델 예산 초과 | model / model_budget_exceeded | HTTP 취소. 확보 결과를 보존해 상태 결정 | `backend/tests/test_agent_budget.py:test_wall_clock_timeout_cancels_the_inflight_http_request`, `test_all_model_steps_share_one_deadline` |
| 인용 누락·없는 숫자 | answer / answer_not_grounded | 근거 없는 설명을 성공으로 확정하지 않고 등록 결과 설명으로 대체하거나 NEEDS_DATA | `backend/tests/test_agent_stability.py:test_thousands_separators_match_tool_json_but_invented_values_do_not` |
| 관측 stale / missing | 도구 결과 observation_quality + reply 범위별 처리 | 상태 확인에 오래된 자료가 쓰이면 NEEDS_DATA. live 실패를 과거 관측으로 대체하지 않음. 이 자료 상태 자체를 새로운 failure code로 만들지 않음 | `backend/tests/test_agent_facility.py:test_missing_and_stale_observations_are_not_a_present_safety_verdict`, `test_live_source_failure_does_not_leak_key_or_substitute_replay` |
| 조건 모호·물리 효과 미지원 | router / answer의 clarification | NEEDS_DATA와 현재 계산 불가 범위. 수리모형이 없는 피해 감소량은 만들지 않음 | `backend/tests/test_agent_stability.py:test_outage_still_refuses_physical_effects_without_running_tools` |

기존 status는 **ANSWERED / NEEDS_DATA / UNAVAILABLE**뿐이다. HTTP 200이어도 NEEDS_DATA·UNAVAILABLE일 수 있다. 422 입력 오류·404 범위 오류·429 요청 제한 등 HTTP 계층을 status enum에 추가하지 않는다.

### 현재 검증의 한계와 다음 실험

구현된 것은 도구 계약, 수치·인용 가드, 도메인 안전 표현, 실패·trace 수집이다. `_grounded_answer`는 숫자가 JSON 어딘가에 존재하는지 보는 가드로, 단위·주어·시점·인과가 맞는다는 증명은 아니다. 실패하지 않은 도구의 숫자를 잘못된 대상에 붙이거나, 숫자 없는 인과 주장을 하는 경우의 탐지율은 미측정이다.

다음 회귀 후보는 **같은 숫자를 다른 관측소·단위에 연결하는 답변**과 **숫자 없이 안전/피해 감소를 단정하는 답변**이다. 실제 결과와 함께 판독 기준을 먼저 고정하고 [평가 절차](AGENT_VALIDATION.md#동일-질문-회귀-비교-절차-2026-10-20)를 따른다. 새 상태·코드·프레임워크 도입은 이 문서 작업에 포함하지 않는다.



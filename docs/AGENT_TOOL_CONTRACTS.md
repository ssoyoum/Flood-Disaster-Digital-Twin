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

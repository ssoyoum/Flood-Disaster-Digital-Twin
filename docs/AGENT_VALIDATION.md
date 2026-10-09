# Agent 연결 검증·진단

작성일: 2026-10-09. 자동 테스트와 실제 Gemini 연결 검증을 구분한다. 오송 소수 질문의 실제 연결 결과는 [평가 기록](AGENT_EVALUATION_RESULTS.md)에 있으며 전체 질문의 모델 성공률 측정 결과는 아니다.

## 시간 예산

`POST /api/agent/ask`는 `AGENT_ASK_TIMEOUT_SECONDS`(기본 25초)를 모든 모델 결정과 잘못된 JSON 재시도에 공유한다. 각 HTTP 요청은 남은 시간만 사용하며 `asyncio.wait_for`로 응답을 계속 보내는 연결도 취소한다. 0·음수·NaN·무한대·잘못된 설정은 기본값으로 돌아간다.

예산은 요청 시작부터 계산한다. 초과하면 새 모델 요청을 보내지 않고 확보한 도구 결과를 반환하거나, 질문에 명시된 값으로 등록 도구를 실행한다. 로컬 도구 계산·응답 직렬화 시간은 추가될 수 있으므로 모든 API 응답이 정확히 25초 내 도착한다는 보장은 아니다. 최대 모델 단계 6회·성공 도구 호출 4회는 유지한다. `/api/agent/plan`의 별도 10초 설정은 변경하지 않았다.

프런트엔드는 질문 1,000자·최근 대화 6개·각 대화 1,500자를 API 계약에 맞춘다. 대화 이력은 Unicode 코드 포인트로 자르며 서버가 계산 근거로 보는 과거 사용자 질문은 유지한다. 사건 전환·컴포넌트 종료 시 브라우저 요청을 취소하고 이전 응답을 버린다. 브라우저 취소만으로 이미 시작한 서버 작업이 즉시 중단되는 것은 아니며 서버 측 모델 예산은 계속 적용된다.

## 응답에서 실패 위치 확인

Swagger 또는 브라우저 네트워크의 `/api/agent/ask` 응답에서 `diagnostics`를 확인한다. API 키·질문·파라미터·예외 원문은 이 필드에 포함하지 않는다. 사용자 화면에는 기존 답변과 도구 근거를 보여 준다.

```json
{
  "request_id": "요청별 고유 식별자",
  "duration_ms": 25010,
  "model_steps": 2,
  "model_requests": 2,
  "completion_source": "registered_tools",
  "failures": [
    {"stage": "model", "code": "model_budget_exceeded", "step": 2, "tool_name": null}
  ]
}
```

위 숫자는 필드 설명용 예시다. 실제 측정값이 아니다. `model_steps`는 루프의 모델 판단 시도 수, `model_requests`는 JSON 재시도를 포함한 HTTP 호출 시도 수다. 키 부재 등 사전 점검 실패는 steps에는 포함되지만 requests에는 포함되지 않는다.

| completion_source | 의미 |
|---|---|
| model | 모델의 최종 결정을 처리한 경로. NEEDS_DATA 또는 근거 검사 실패도 있으므로 설명 성공을 뜻하지 않음 |
| registered_tools | 모델 설명 대신 등록 도구 결과를 반환 |
| capability | 모델 없이 사용법·예시 질문 반환 |
| clarification | 모델 없이 모호한 후속 조건의 확인 요청 반환 |
| unavailable | 모델 실패 후 반환 가능한 도구 결과도 없음 |

| stage / code | 확인할 것 |
|---|---|
| model / model_unavailable | `/api/agent/planner-status`와 서버의 GEMINI_API_KEY 설정. status.available은 실제 호출 성공이 아님 |
| model / model_connection_failed | 서버 네트워크·TLS·연결 상태 |
| model / model_http_error | limitations의 HTTP 상태. 키·할당량·모델 설정은 서버에서 확인 |
| model / model_budget_exceeded | 전체 대기 예산 초과. 단계별 재시도로 예산을 새로 시작하지 않음 |
| model / model_invalid_decision | 응답 JSON·스키마가 맞지 않음. 최대 1회 재시도 |
| validation / tool_input_rejected | 사건에 없는 도구, 사용자 미입력 값, 범위 오류, 중복 도구 요청 |
| tool / tool_execution_failed | 검증을 통과한 호출의 자료·분석 실행 실패 |
| answer / answer_not_grounded | 최종 답변의 인용·수치 근거 검사를 통과하지 못함 |

## 후속 질문의 조건

`diagnostics.context_mode`는 `current`(이번 질문), `reused`(직전 사용자 조건 재사용), `updated`(같은 분석의 새 값), `ambiguous`(확인 필요)다. `context_note`는 화면에서 조건을 이어받거나 바꿨음을 알려 준다.

- “08:20에 통제했다면?” 뒤 “그 조건으로 다시 비교해줘”는 같은 조건을 재사용한다.
- 그 뒤 “그럼 08:10은?”은 08:20을 남기지 않고 08:10으로 바꾼다. 지연 분·경보 임계·대응 시각도 단위를 확인해 처리한다.
- 사용자 질문만 조건의 출처가 된다. Assistant가 제안한 숫자나 중간에 다른 주제로 바뀐 대화의 과거 숫자는 빌려오지 않는다.
- 복수 분석, 기준이 모호한 상대 시간, 다른 분석 종류, 부적합한 숫자는 임의로 합치지 않고 확인을 요청한다. 이 기능이 모든 자연어 표현을 이해한다는 뜻은 아니다.
- 모델은 서버가 결정한 `parameter_context`에 있는 값과 허용된 사건 단계 시각만 도구에 전달할 수 있다. 호출 기록은 검증·정규화 후 실제 실행한 파라미터를 표시한다.

## 실제 연결 대조 표

실제 모델 확인은 개발자가 명시적으로 실행한다. API 요청마다 모델 비용이 발생할 수 있으며 이 작업의 자동 테스트는 네트워크와 모델을 모의하여 실제 Gemini를 호출하지 않는다. 성공률 분모는 도움말을 제외한 실제 시도 요청이다. 모델 설명과 도구 결과 폴백을 나누어 기록한다.

| 사건 / 질문 | 기대 경로·대조 근거 |
|---|---|
| 오송 / 08:20에 통제했다면? | analyze_closure_timing, 동일 조건 직접 분석과 7분 일치 |
| 오송 / 유입을 10분 늦췄다면? | analyze_inflow_delay, 직접 분석의 이동 시각과 일치 |
| 오송 / HAND 선택 임계를 1.5m 낮추면? | analyze_hand_threshold, 셀 민감도 설명. 제방·피해 효과로 해석 금지 |
| 오송 / 제방을 1m 높였다면? | 물리 효과 계산을 거부하고 자료·모형 한계 설명 |
| 오송 / 앞선 질문 후 “그 조건으로 다시 비교해줘” | 과거 사용자 값만 사용, 값 누락 시 확인 요청. 폴백이 문맥을 추측해 새 값을 생성하지 않음 |
| 서울 / 신림 강우계가 시간당 95mm를 넘었을 때 경보를 보냈다면? | analyze_alert_timing, 동일 임계 직접 분석과 일치 |
| 서울 / 신월 규모 저류시설이 도림천에 있었다면? | analyze_storage_capture, 등록 320000m³와 직접 분석 일치 |
| 포항 / 진입 금지 안내를 30분 일찍 했다면? | analyze_response_timing, 실제 안내 기준 06:00 환산·직접 분석 일치 |
| 안동 / 23:40에 대피명령을 냈다면? | analyze_response_timing, 경보 수위 도달 예측까지 50분. 언론 보도임을 명시 |
| 사건 전환 / 오송 질문 중 서울로 전환 | 오송 답변·대화가 서울에 섞이지 않음, 서울에서 새 질문 가능 |

각 요청의 버전·event_id·질문·status·completion_source·duration_ms·도구명·파라미터·직접 분석 대조·실패 코드를 비공개 기록에 남긴다. 사례마다 관측·보도·재구성의 경계를 확인한다. 원인 확인 전에는 키 설정이나 모델 종류가 문제라고 단정하지 않는다.

## 자동 검증 명령

```powershell
python -m pytest backend/tests -q
npm test
npm run build
npm run test:e2e
```

직접 분석 API 대조 평가:

```powershell
python backend/evaluation/evaluate_agent.py --output docs/local/agent-eval-offline.json
python backend/evaluation/evaluate_agent.py --mode live --limit 4 --output docs/local/agent-eval-live.json
```

기본 offline은 모델 없이 13개 질문의 API·도구·조건·분석 수치를 대조한다. 로컬 평가 프로세스에서만 요청 한도를 올리며 공개 서버 설정은 바꾸지 않는다. live는 설정한 실제 Gemini를 사용하고 설정된 요청 한도를 유지한다. `--case reuse-closure --case update-closure`처럼 질문을 선택할 수 있다. live 입력량·횟수는 한도와 비용을 고려해 제한한다.

종료 코드 0은 선택한 대조 검사 통과, 1은 검사 실패, 2는 실제 모델 설정 불가다. JSON은 답변·정규화 입력·진단·검사별 통과 여부를 남긴다. 자동 대조는 선택한 결과 필드를 검사하므로 답변의 의미와 인과 주장은 사람이 추가로 읽어 확인한다.

회귀 범위: HTTP 취소, 재시도·여러 단계의 공유 예산, 입력 검증과 도구 실패 구분, 요청별 상태 초기화, 긴 후속 대화, 요청 중 사건 전환. 실제 서비스 배포·실제 모델 안정성·기관 파일럿은 별도 검증이다.


## 시설 범위 대조 (2026-10-10)

시설 범위는 [FACILITY_AGENT.md](FACILITY_AGENT.md)를 따른다. 기존 사건별 분석은 별도 범위로 유지하며, 시설 카탈로그는 상태·규칙·백테스트 세 도구뿐이다. 모델의 시설·시각 변경 거절, 누락·지연 관측, 실시간 실패 시 과거 자료 대체 금지, 키 포함 오류 비노출, 명시적 재생의 live 조회 금지, 근거 없는 안전·통제 완료 주장 폴백을 검증한다. 브라우저에서 범위 변경과 시각 입력 뒤 추천 질문 유지도 확인한다.

```powershell
python backend/evaluation/evaluate_agent.py --suite facility --output docs/local/facility-agent-offline.json
python backend/evaluation/evaluate_agent.py --suite facility --mode live --output docs/local/facility-agent-live.json
```

시설 suite의 `live`는 실제 Gemini 모드이며 관측은 replay로 고정한다. 실시간 관측·공개 배포 검증과 구분한다. 실제 모델 답변에도 DQ-009 시각 차이와 상승 속도 외삽의 한계를 유지한다.

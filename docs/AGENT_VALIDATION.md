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
| validation / tool_selection_rejected | 등록되지 않은 도구, 또는 이 사건·시설 범위에 없는 도구를 모델이 고름 |
| validation / tool_input_rejected | 사용자 미입력 값, 범위 오류, 사건·시설·시각을 모델이 바꾼 요청 |
| validation / tool_call_repeated | 이미 실행한 같은 도구·같은 파라미터를 다시 요청 |
| tool / tool_execution_failed | 검증을 통과한 호출의 자료·분석 실행 실패 |
| answer / answer_not_grounded | 최종 답변의 인용·수치 근거 검사를 통과하지 못함 |

### 단계별 trace와 토큰 (2026-10-15)

`diagnostics.trace`는 요청 하나의 경로를 순서대로 남긴다. 각 단계는 `seq`·`stage`·`outcome`·`ms`·`tool_name`·`by`(누가 실행했는지)이며, failures와 같은 규칙으로 질문 원문·파라미터 값·도구 결과·예외 원문은 넣지 않는다.

| stage | outcome 예 | 의미 |
|---|---|---|
| router | current / reused / updated / ambiguous | 서버가 질문에서 조건과 추천 도구를 정한 단계 |
| model | decision_tool / decision_final / model_* 오류 코드 | 모델 판단 1회(JSON 재시도 포함) |
| validation | accepted / tool_selection_rejected / tool_input_rejected / tool_call_repeated | 모델이 고른 도구·인자 검증 |
| tool | ok / tool_execution_failed | 도구 실행. `by=model`은 모델 선택, `by=server`는 질문에 적힌 값으로 서버가 실행 |
| answer | grounded / answer_not_grounded / model_limitation / fixed_limitation | 최종 답변의 근거 검사와 한계 설명 경로 |
| reply | answered / needs_data / unavailable | 응답 상태, `by`는 completion_source |

`diagnostics.tokens`는 Gemini 응답의 `usageMetadata`를 요청 단위로 합한 값(`prompt`·`output`·`thoughts`·`total`·`responses`)이다. 모델 응답이 없으면 `null`이다.

서버 쪽 기록이 필요하면 `FLOODOPS_AGENT_TRACE_LOG`에 파일 경로를 지정한다. 요청마다 JSON 한 줄(요청 ID·사건·시설·상태·도구 순서·근거 번호·diagnostics)을 덧붙이며, 질문·파라미터·도구 결과는 쓰지 않는다. 지정하지 않으면 쓰지 않는다. 화면의 `request_id`로 같은 줄을 찾아 UI 도구 이력과 대조한다.

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


## 고정 벤치마크 (2026-10-15)

`backend/evaluation/agent_benchmark_cases.json` 39문항을 7개 유형(정상 8·도구 선택 8·모호 5·자료 부족 4·잘못된 입력 5·도구 실패 3·안전 표현 6)으로 나눈다. 각 문항은 기대 상태, 호출해야 할 도구와 파라미터, 호출하면 안 되는 도구, 반드시 포함할 표현, 금지 주장(정규식)을 가진다. 도구 실패 문항은 평가 프로세스 안에서만 해당 도구가 예외를 내도록 바꾼다.

```powershell
python backend/evaluation/agent_benchmark.py --output docs/local/agent-benchmark-offline.json
python backend/evaluation/agent_benchmark.py --mode live --seconds-per-request 5 --output docs/local/agent-benchmark-live.json
```

offline은 모델을 장애 상태로 두고 `needs_model` 6문항을 뺀다. live는 39문항 전부를 실제 Gemini로 보낸다. 로컬 단일 프로세스라 공개 서버용 요청 한도는 두 모드 모두 풀지만, Gemini의 분당 한도는 그대로라 `--seconds-per-request`로 간격을 둔다. 간격 없이 돌리면 HTTP 오류가 섞여 품질이 아니라 한도를 재게 되며, 그런 문항은 요약의 `model_transport_errors`에 나온다.

지표: 문항 통과율, 도구 정확도(기대·금지 도구 조건이 있는 문항), 근거 유효성(근거 번호가 있는 답변의 인용·수치 검사), 근거 없는 주장 비율(금지 주장 또는 모델 답변의 출처 없는 숫자), 모델 요청 수, 토큰, p50/p95 지연. 보고서에는 git 커밋, Agent 코드 미커밋 여부, 모델 ID, 시스템 프롬프트·문항 파일 해시가 함께 남는다. 직접 분석 API와 값이 같은지는 기존 `evaluate_agent.py`가 계속 맡는다.

## Ollama 공급자와 3주차 측정 도구 (2026-10-15)

`AGENT_LLM_PROVIDER=ollama`이면 `/api/agent/ask`의 모델 판단을 로컬 Ollama `/api/chat`으로 보낸다. 시스템 프롬프트·카탈로그·검증·근거 검사는 Gemini와 같고, 응답 형식은 `AgentAction` JSON 스키마로 강제한다. 기본값은 Gemini이며 공개 서버 설정은 바꾸지 않았다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `AGENT_LLM_PROVIDER` | gemini | `ollama`이면 로컬 모델 사용 |
| `OLLAMA_BASE_URL` | http://localhost:11434 | |
| `OLLAMA_MODEL` | qwen2.5:3b | 응답의 `model`은 `ollama:<이름>` |
| `OLLAMA_NUM_CTX` | 16384 | Ollama 기본 문맥(2~4k)보다 프롬프트가 길어 늘림. 넘으면 Ollama가 조용히 자른다 |
| `AGENT_ASK_TIMEOUT_SECONDS` | Ollama 300 / Gemini 25 | CPU 추론은 판단 1회에 1~3분 걸린다 |

토큰은 `prompt_eval_count`·`eval_count`를 `diagnostics.tokens`에 같은 이름으로 합산한다. 연결 실패는 `model_connection_failed`, 시간 초과는 `model_budget_exceeded`다.

```powershell
python backend/evaluation/agent_benchmark.py --mode live --provider ollama --model qwen2.5:3b --case n-osong-closure --output docs/local/agent-benchmark-ollama.json
python backend/evaluation/agent_benchmark.py --mode live --provider gemini --seconds-per-request 5 --no-trim --full-catalogue --output docs/local/agent-benchmark-before-week3.json
python backend/evaluation/prompt_size.py --output docs/local/agent-prompt-size.json
```

`--no-trim`·`--full-catalogue`는 같은 코드에서 3주차 축소(O1 도구 결과의 지도용 필드, O2 카탈로그 중복 필드)를 끈 비교 측정용이다. 제품에는 이런 스위치가 없다. `prompt_size.py`는 모델을 부르지 않고 문항마다 정해진 도구 순서로 루프를 돌려, 판단마다 실제로 보내질 프롬프트 길이(시스템 프롬프트 + 컨텍스트, 자)를 세므로 실행마다 같은 값이 나온다. Gemini 일일 할당량이 끝나면 HTTP 429로 모든 문항이 `model_transport_errors`에 들어가므로, 그 실행은 품질 측정으로 쓰지 않는다.

## 시설 범위 대조 (2026-10-10)

시설 범위는 [FACILITY_AGENT.md](FACILITY_AGENT.md)를 따른다. 기존 사건별 분석은 별도 범위로 유지하며, 시설 카탈로그는 상태·규칙·백테스트에 기준 비교·연구 상승 모델을 더한 다섯 도구다(2026-10-15). 모델의 시설·시각 변경 거절, 누락·지연 관측, 실시간 실패 시 과거 자료 대체 금지, 키 포함 오류 비노출, 명시적 재생의 live 조회 금지, 근거 없는 안전·통제 완료 주장 폴백을 검증한다. 브라우저에서 범위 변경과 시각 입력 뒤 추천 질문 유지도 확인한다.

```powershell
python backend/evaluation/evaluate_agent.py --suite facility --output docs/local/facility-agent-offline.json
python backend/evaluation/evaluate_agent.py --suite facility --mode live --output docs/local/facility-agent-live.json
```

시설 suite의 `live`는 실제 Gemini 모드이며 관측은 replay로 고정한다. 실시간 관측·공개 배포 검증과 구분한다. 실제 모델 답변에도 DQ-009 시각 차이와 상승 속도 외삽의 한계를 유지한다.

## 동일 질문 회귀 비교 절차 (2026-10-20)

이 절은 기존 평가 스크립트의 사용·비교 계약이다. 별도 AGENT_EVALUATION_PLAYBOOK을 만들지 않는다. 과거 측정값은 [AGENT_EVALUATION_RESULTS.md](AGENT_EVALUATION_RESULTS.md)에만 유지하고, 아래 표의 미측정을 과거 통과 수치로 채우지 않는다.

### 먼저 저장할 기준선

1. 비교 전 코드 commit, 질문 JSON SHA-256, 데이터 manifest/입력 hash, Python·패키지 버전, provider·model·온도 설정, replay/live 모드를 적는다.
2. 현재 검색/도구 경로의 **기준선 보고서부터 보관**한다. 새 후보가 통과한 뒤 기대 도구·기대 숫자·금지 주장 정규식을 바꾸지 않는다. 평가 케이스는 `backend/evaluation/agent_ask_cases.json`, `agent_facility_cases.json`, `agent_benchmark_cases.json`이 기준이다.
3. 같은 case ID와 자료 시점으로 변경 후를 측정한다. offline과 live, cold start와 warm request, historical과 facility를 섞어 한 성공률로 만들지 않는다.
4. 도구 선택·직접 서비스 결과 대조와 최종 자연어의 근거 일치·주장 정확도를 따로 비교한다. offline의 서버 폴백 성공은 LLM 선택 성공이 아니다.

### 검증한 옵션과 실행 범위

아래 명령은 코드의 argparse·package scripts를 확인했으며 **이번에 실행하지 않았다.** 원본 전체 checkout·처리 자료·의존성이 있는 환경에서 실행한다.

```bash
python backend/evaluation/evaluate_agent.py --mode offline --suite historical --output docs/local/baseline-historical.json
python backend/evaluation/evaluate_agent.py --mode offline --suite facility --output docs/local/baseline-facility.json
python backend/evaluation/agent_benchmark.py --mode offline --output docs/local/baseline-benchmark.json
```

- `evaluate_agent.main`: --mode offline/live, --suite historical/facility, --case(반복), --limit, --output. facility는 replay로 고정한다. offline 구현은 `_gemini_action`을 장애로 mock하므로 기존 환경의 AGENT_LLM_PROVIDER가 ollama이면 별도 검토 없이 “무외부 모델 평가”라고 가정하지 않는다. 실행 환경은 **AGENT_LLM_PROVIDER=gemini**, 키·개발자 .env 유입 차단 조건을 기록한다.
- `agent_benchmark.main`: --mode, --case, --category, --output, --seconds-per-request, --provider, --model, --no-trim, --full-catalogue. offline이 needs_model 케이스를 건너뛰는 점을 분모에 표시한다.
- 테스트 명령은 기존 절의 `python -m pytest backend/tests -q`, `npm test`, `npm run build`를 재사용한다. E2E는 `playwright.config.ts`가 FastAPI 8035·Vite 5175 두 서버, replay 모드, GEMINI_API_KEY 공백을 설정한다. Playwright 브라우저·Node/Python 의존성·자료가 필요하며 “서비스가 전혀 필요 없다”는 뜻은 아니다.
- offline은 모델을 부르지 않는 경로이지 모든 외부 자료 연동을 자동 mock하는 보장이 아니다. 각 케이스의 도구와 관측 모드를 확인한다.

### 지표와 분모

| 지표 | 실제 자동 계산 / 제안 | 판독 |
|---|---|---|
| 도구 선택 정확도 | benchmark의 tool_accuracy, tool_ok가 있는 케이스만 | 기대 도구·인자 충족 및 금지 도구 미호출. 도구 없음 케이스를 무조건 정답에 포함하지 않음 |
| 상태 판정 | status 검사 + task_success_rate | 허용 상태와 HTTP를 별개로 기록. 정답 보류 NEEDS_DATA도 성공 가능 |
| 근거 가드 통과율 | evidence_validity | 인용이 있는 답변 대상으로 _grounded_answer 검사. null인 답변은 미측정이며 0이나 1로 채우지 않음 |
| unsupported claim rate | unsupported_numbers + must_not_claim 정규식 | 모델 경로 숫자 대조·사전 금지 표현 탐지 범위. 의미 전체의 환각률이 아님 |
| 직접 계산 대조 | evaluate_agent의 results_match | 등록 compare_keys만 대조. 모든 결과 필드를 검증했다는 주장은 불가 |
| 지연 | diagnostics.duration_ms의 p50/p95/max | 프로세스 내부 경로 기준. 외부 부하·네트워크 포함 운영 SLO와 구분 |
| 토큰·비용 | tokens 집계 구현 / 통화 비용 환산은 제안 | provider 응답에 토큰이 없는 경우 null. 실행 시점 가격표·입출력 단가·환율 없이 원화 비용을 만들지 않음 |
| 의미·인과 일치 | **사람 판독 제안** | 주장별 근거 도구·필드·시점·단위, 자료 없는 경우 보류 여부를 표시 |

### 결과 기록 양식

| 실행 | commit / 질문·자료 hash | 모드·분모·skip | 도구 정확도 | 상태/전체 성공 | 근거 가드 n | 금지 주장 n | p50/p95 ms | 토큰·비용 | 판독·원본 |
|---|---|---|---|---|---|---|---|---|---|
| 기준선 | 실행 전 고정 | 미실행 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | report 경로 |
| 변경 후 | 같은 조건·후보 commit | 미실행 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | report 경로 |

케이스별로 기대 도구/인자·금지 도구·허용 상태·핵심 주장·보류 조건·실패 단계·completion_source도 보존한다. 필수 회귀는 ① 재현 가능한 실패가 발생했거나 ② 입력 계약·자료 신선도·금지 주장이 바뀔 때 추가한다. 기존 케이스가 같은 위험을 검사하면 중복하지 않는다.

### Live 평가 승인·중단 조건

Live LLM 평가는 질문·history·도구 결과를 외부 provider로 전송하고 요청량/비용을 사용한다. **실행할 case ID·모델·최대 요청량·예상 토큰/상한을 먼저 정해 승인받기 전에는 실행하지 않는다.** Ollama도 외부 유료 API와 구분하되 로컬 프로세스·시간·메모리 비용과 실제 실행 의존성을 기록한다. 예산 초과·반복 HTTP quota 오류 시 중단하고, 해당 실패를 모델 추론 품질 하락으로 해석하지 않는다.

다음 실험 하나: 기존 benchmark를 고정한 offline 기준선을 먼저 저장하고, 숫자·인용을 만족해도 주어·시점이 틀린 답변을 사람이 판독한다. 이 작업은 문서 설계만 했으며 결과 JSON을 생성하거나 테스트 통과를 주장하지 않는다.



## trace 집계 실행 (2026-10-20)

`backend/evaluation/summarize_traces.py`는 기존 opt-in JSONL을 읽어 요청 ID 중복·깨진 줄을 구분하고, 기존 ANSWERED/NEEDS_DATA/UNAVAILABLE 상태·실패 stage/code·도구 호출·p50/p95/max·모델 요청·보고된 토큰을 집계한다. 질문·응답·도구 payload는 출력하지 않는다. 빈 로그/잘못된 줄은 CLI 실패이며, 측정 불가 지표를 0% 성공으로 바꾸지 않는다.

```bash
FLOODOPS_AGENT_TRACE_LOG=/tmp/agent-traces.jsonl python backend/evaluation/agent_benchmark.py --mode offline --output /tmp/agent-benchmark.json
python backend/evaluation/summarize_traces.py /tmp/agent-traces.jsonl --output /tmp/agent-trace-summary.json
```

새 trace 파일로 실행해야 서로 다른 실험이 섞이지 않는다. 이번 offline 37문항 중 HTTP 응답 계약에 들어온 34건이 집계됐다. ANSWERED 23·NEEDS_DATA 8·UNAVAILABLE 3, 모델 요청 0, p95 1,464ms였다. 오류 주입·키 없는 경로를 포함한 합성 평가이며 운영 지연/SLA가 아니다. 평가 성공 37/37과 ANSWERED 비율 23/34는 서로 다른 지표다. 422 등 Agent 실행 전 HTTP 거절·프로세스 소실은 이 로그 밖이며 별도 access log가 필요하다. 토큰 미보고는 비용이 0이라는 뜻이 아니고 이번 실행의 model_requests=0과 함께 해석한다. 의미·주어·시점·인과 정확성도 이 집계로 입증되지 않는다.

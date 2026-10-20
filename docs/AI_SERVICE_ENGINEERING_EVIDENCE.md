# AI 서비스 엔지니어링 증거

확인일: 2026-10-20. 등록 도구 기반 실행 구조와 실제 검증 결과를 연결한다. 토목·수자원 지식은 계산·자료 해석의 한계를 정하는 데 사용하며, 모델이 계산값이나 통제 효과를 만들도록 맡기지 않는다.

## 구현과 채용 역량 연결

| 역량 유형 | 실행 가능한 근거 | 설명할 수 있는 것 | 아직 입증하지 못한 것 |
|---|---|---|---|
| AI 서비스·Agent 백엔드 | `backend/app/main.py:ask_agent_question` → `agent_runner.ask_agent` → `_validated_tool_request` → `agent_tools.execute_agent_tool` | 모델은 등록 도구를 선택하고 서버는 scope·입력·실행을 통제 | 범용 자율 에이전트·모든 오류의 자동 복구 |
| API·오류 처리 | `schemas.AgentAskRequest` / `AgentAskResult`, `agent_runner._reply` | HTTP 계약과 ANSWERED/NEEDS_DATA/UNAVAILABLE, 자료 부족·실패 응답 분리 | 대규모 부하·운영 SLA |
| 근거·진단 | `_grounded_answer`, `_write_trace_log`, diagnostics | 인용·숫자 가드와 요청별 trace·실패·토큰 추적 | 의미·주어·시점·인과 전체의 정확성, 환각 0% |
| 평가 자동화 | `backend/evaluation/agent_benchmark.py`, 고정 case JSON | 동일 질문의 상태·도구·금지 주장·근거 가드 검사 | offline 성공으로 Live 모델 정확도 증명 |
| 회귀·CI | `.github/workflows/ci.yml`, `backend/tests/`, `package.json` | PR/main에서 백엔드·offline benchmark·프런트 검사 후 이미지 build와 smoke | 현재 원격 run 성공은 Actions에서 별도 확인 |
| 컨테이너 실행 | `Dockerfile.aws`, 네트워크 없는 컨테이너 smoke | FastAPI·정적 프런트·사건 데이터의 이미지 기동 확인 | 신규 AWS 배포, EKS·PostGIS 운영 |

위 직무 연결은 AI 서비스/API·Agent 실행·검증 자동화라는 **일반 역량 유형**에 대한 해석이다. 특정 현재 채용 공고의 요구사항을 조회하거나 일치도를 채점한 결과는 아니다. 지원할 때 실제 공고의 요구 문장과 담당 범위를 추가 대조한다.

## 이번 실행 결과

기준 소스는 `8433fe969ff0a98a27eba2d19f513083ca42843a`의 새 checkout이며 CI와 테스트 수정 후 아래 결과를 얻었다. 생산 분석 코드·자료·가중치·프롬프트는 바꾸지 않았다.

| 검사 | 실제 결과 | 범위·한계 |
|---|---|---|
| Python 3.12.14 + backend/requirements.txt, 전체 pytest | 322 passed | 최초 312 passed/6 failed에서 미추적 이미지 의존·오래된 도구/시설/지역 가정을 보완. 테스트 제거/신규 skip 없음 |
| `npm test` | 3 files / 7 tests passed | 브라우저 E2E 아님 |
| `npm run build` | 성공 | 로컬 Node 24.19.0. CI와 Docker의 Node 22와 구분. 번들 크기 경고는 남아 있음 |
| offline Agent benchmark | 37/37, needs_model 6문항 제외 | model_requests 0. tool_accuracy 25문항, evidence_validity 9문항; 전체 Live 정확도 아님 |
| Docker image build | 성공, image SHA `013ea482dd23377feda653685d83362863f8f1f355e89975323428fb4fdefd0e` | 로컬 프록시 CA를 secret mount한 임시 Dockerfile로 TLS trust만 보완. 저장소 Dockerfile.aws는 변경하지 않음 |
| 네트워크 없는 이미지 기동 smoke | /health 200, /api/events 5건, / 200 | 일회성 로컬 컨테이너 확인 후 삭제. 실제 배포/모든 데이터 완전성 검증 아님 |

오프라인 평가 JSON과 junit 원본은 이번 작업 환경의 `/tmp/floodops-benchmark-baseline.json`, `/tmp/floodops-backend-final.xml`에 있다. 향후 CI는 reports를 7일 보관한다. 임시 파일을 장기 보관되는 원격 증거로 인용하지 않는다.

재현 명령은 [AGENT_VALIDATION.md](AGENT_VALIDATION.md), 실행 경계·실패별 테스트는 [AGENT_TOOL_CONTRACTS.md](AGENT_TOOL_CONTRACTS.md), CI의 실제 범위는 [CI_CD_DESIGN.md](CI_CD_DESIGN.md)를 사용한다.

## 취업·제품화에서 다음에 증명할 것

현재 강점은 수자원 자료의 관측·재생·연구값을 구분하고, 실패 시 계산을 보류하는 서비스 실행 계약이다. 구현 코드의 존재와 본인 역할·직접 작성 범위는 별도 기여 기록으로 입증한다.

다음 작업 하나는 실제 시설 관리 업무 담당자에게 **어떤 자료와 설명이 통제 검토 시간을 줄이는지** 확인하는 작은 검토다. 입력 자료·판독 기준·담당자 피드백·오판 위험을 기록하고, 반복 사용자·가치 검증 전에는 유료 B2B 가능성이나 비용 절감 성과를 확정하지 않는다. 자동 통제나 피해 예측을 판매 범위로 선언하지 않는다.

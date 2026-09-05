# FloodOps 작업 지침

## 커밋 메시지 형식

모든 커밋은 아래 형식을 따른다.

```
type(scope): 영어로 짧게 핵심 요약

한글로 "왜/무엇을" 설명했습니다.

- 실제 변경 1
- 실제 변경 2
- 실제 변경 3
```

규칙:

- subject는 영어로 짧게 쓴다. 동사로 시작한다(`add`, `return`, `clarify`, `pin`).
- 본문 첫 줄은 한글 한 문장으로 **왜 / 무엇을** 했는지 쓰고 `했습니다.`로 끝낸다.
- 그 아래 실제 변경을 불릿 3개로 쓴다. 바뀐 파일 목록이 아니라 무엇이 달라졌는지를 쓴다.
- 수치·엔드포인트·플래그처럼 확인 가능한 값을 쓴다. 추정해서 쓰지 않는다.
- **작업 주체를 쓰지 않는다.** `Co-Authored-By` 트레일러를 붙이지 않고, 어떤 도구가 작업했는지 본문에도 쓰지 않는다.

예시:

```
fix(agent): load local .env so the LLM credential reaches the planner

`.env`에 넣은 키가 planner에 보이지 않던 문제를 고쳤습니다. uvicorn은 `--env-file` 없이 `.env`를 읽지 않고 pytest는 아예 읽지 않습니다.

- `_load_env_file_once()`로 저장소 루트 `.env`를 최초 1회만 로드
- 실제 환경변수가 항상 우선하도록 `override=False` 적용
- `python-dotenv==1.0.1` 추가하고 미설치 시에는 조용히 건너뛰도록 처리
```

## 커밋 스코프

새 스코프를 만들지 말고 아래에서 고른다.

| type | scope | 대상 |
| --- | --- | --- |
| `feat`, `fix` | `api` | FastAPI endpoint, service, schema |
| `feat`, `fix` | `agent` | Agent Tool, planner, workflow |
| `feat`, `fix` | `frontend` | React, MapLibre, CSS |
| `feat`, `fix` | `data` | `data/` 산출물, 처리 스크립트 |
| `feat`, `fix` | `osong` `hydromet` `safemap` `dssp` | 특정 데이터 출처·사건 도메인 |
| `docs` | `osong` `agent` | 해당 도메인 문서 |
| `docs` | 없음 | README, PROJECT_PLAN 등 저장소 전체 문서 |
| `chore` | `repo` | `.gitignore`, 실행 설정, 저장소 구성 |

주의:

- 스코프는 **항상 괄호 안**에 넣는다. `:` 앞은 타입 자리다.
- `data`는 스코프다. `data: ...`처럼 타입 자리에 쓰면 스코프로 인식되지 않는다.
- 코드 위치와 도메인 중 **코드 위치를 우선**한다. 오송 관련이어도 백엔드 코드를 고쳤으면 `feat(api)`다.

## 브랜치와 푸시

여러 도구(Claude Code, Codex)로 같은 저장소를 작업하므로 이력이 갈라지기 쉽다.

- **푸시된 커밋은 리베이스하지 않는다.** patch-id가 같은 중복 커밋이 생기고 로컬과 원격이 갈라진다.
- **작업 시작 전 `git fetch`로 원격 상태를 먼저 확인한다.** 로컬에만 오래 쌓아두지 않는다.
- **커밋안을 먼저 보여주고 확인을 받은 뒤에 푸시한다.** 커밋 메시지와 파일 묶음을 제시하고, 확인이 오면 그때 푸시한다. 확인 없이 임의로 푸시하지 않는다. 확인이 온 뒤에는 미루지 않는다 — 미푸시 커밋이 쌓일수록 갈라질 확률이 올라간다.
- **같은 브랜치를 두 도구가 동시에 만지지 않는다.** 병행이 필요하면 브랜치를 나누고 PR로 합친다.
- **메시지는 커밋할 때 완성한다.** 나중에 몰아서 reword하면 이력 재작성이 필요해지고, 그게 위 문제를 부른다.

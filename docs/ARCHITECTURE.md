# FloodOps Architecture

이 문서는 현재 저장소의 실행 구조를 설명한다. 제품 목표와 MVP 범위는 [PROJECT_PLAN](PROJECT_PLAN.md), 코드 작성 규칙은 [DEVELOPMENT_GUIDE](DEVELOPMENT_GUIDE.md), 데이터 규칙은 [DATA_GUIDE](DATA_GUIDE.md)를 기준으로 한다.

## Runtime Flow

```text
Browser
  -> React application (src/)
  -> API client (src/api.ts)
  -> FastAPI (backend/app/main.py)
  -> domain services and demo data
  -> JSON response
```

현재 화면은 사건 선택, 공간 레이어 조회, 타임라인 확인, 노출 지표 조회, 방재 개입 비교 흐름으로 구성된다.

## Frontend

| 경로 | 역할 |
| --- | --- |
| `src/main.tsx` | React 진입점 |
| `src/App.tsx` | 화면 구성과 사용자 흐름 |
| `src/api.ts` | Backend API 호출 |
| `src/types.ts` | API·도메인 타입 |
| `src/styles.css` | 화면 스타일 |

## Backend

| 경로 | 역할 |
| --- | --- |
| `backend/app/main.py` | FastAPI 라우트와 애플리케이션 진입점 |
| `backend/app/schemas.py` | 요청·응답 스키마 |
| `backend/app/services.py` | 노출 지표와 시나리오 계산 |
| `backend/app/data.py` | 현재 데모 인메모리 데이터 |
| `backend/tests/` | Backend 계약 테스트 |

## Data Flow

```text
External source
  -> data/raw/
  -> validation and processing
  -> data/processed/
  -> manifest metadata
  -> future repository/API integration
```

`data/manifests/event-catalog.yml`은 사건 목록과 기본 사건을 관리하고, `source-availability.yml`은 데이터 출처와 확보 상태를 관리한다.

## Deployment Components

- Vite 개발 서버: Frontend 제공
- FastAPI/Uvicorn: Backend API 제공
- PostgreSQL/PostGIS: Docker 구성에 포함된 후속 저장소
- 현재 기본 실행: Backend 데모 데이터와 Frontend API 계약 검증

## Current Boundaries

## Portfolio Scenario API

The scenario workflow is split into definition and execution so a future
database or simulation worker can replace the current in-memory rule engine:

```text
POST /api/scenarios
  -> validate event and building IDs
  -> save a DRAFT scenario
  -> POST /api/scenarios/{scenario_id}/run
  -> calculate portfolio priority change
  -> return before/after metrics and assumptions
```

Example request:

```json
{
  "name": "Osong building response drill",
  "event_id": "osong-2023",
  "building_ids": [1, 2, 3],
  "interventions": ["flood_barrier", "evacuation_support"]
}
```

The current runner uses the latest derived HAND-like envelope as a spatial
proxy and rule-based intervention factors. It is intentionally marked
`TEMPORARY`; it is not calibrated hydraulics, official Flood Extent, or a
damage-cost model. Swagger is available at `/docs` when the FastAPI server is
running, and the machine-readable contract is `/openapi.json`.

## Agent Tool Boundary

The Agent layer exposes only registered tools that delegate to existing event
repositories and analysis services:

```text
GET  /api/agent/tools
POST /api/agent/tools/{tool_name}
POST /api/agent/plan
POST /api/agent/workflows
  -> plan supported intent without executing a tool
  -> validate event and workflow parameters
  -> call context and analysis tools in sequence
  -> return tool-call trace and domain result
```

The React client uses the same two-step boundary: it displays the plan from
`/api/agent/plan` first, then runs `/api/agent/workflows` only after an explicit
user action. It renders the returned tool trace, assumptions, and limitations;
it does not calculate or rewrite domain metrics in the browser.

The current registry includes event metadata, historical reconstruction,
closure-timing What-if A, inflow-delay What-if B, and envelope-independent
exposure inventory, and baseline scenario comparison. The `situation` workflow returns event and reconstruction
context; analysis workflows chain event context, reconstruction, and one
analysis tool. `compare_scenarios` is intentionally limited to baseline versus
closure/inflow timing measures; it does not produce damage, casualty, depth, or
official inundation estimates. The deterministic intent planner recognizes only these
registered workflows and returns `NEEDS_CLARIFICATION` or `UNSUPPORTED` when
it cannot select one safely. The wrapper does not read GIS files directly, call
external APIs, or invent missing flood measurements. Workflow responses also
promote provenance, coverage status, and coverage notes so the Agent/UI does
not need to infer evidence from an opaque tool trace.

- 실제 PostGIS Repository와 Migration은 아직 연결하지 않는다.
- 과거 사건 자료는 저장된 snapshot을 사용하며 런타임마다 외부 API를 호출하지 않는다.
- 실제 Flood Extent, 관측 강우, 공식 세부 공간인구가 확보되면 데이터 처리 계층을 통해 연결한다.

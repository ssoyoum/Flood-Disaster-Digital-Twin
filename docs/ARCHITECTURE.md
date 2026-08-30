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

- 실제 PostGIS Repository와 Migration은 아직 연결하지 않는다.
- 과거 사건 자료는 저장된 snapshot을 사용하며 런타임마다 외부 API를 호출하지 않는다.
- 실제 Flood Extent, 관측 강우, 공식 세부 공간인구가 확보되면 데이터 처리 계층을 통해 연결한다.

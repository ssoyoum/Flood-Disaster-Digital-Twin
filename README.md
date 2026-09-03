# FloodOps

FloodOps is not a future flood prediction system.

FloodOps is a disaster decision-support Digital Twin PoC that reconstructs real historical disaster events with observed and spatial data, then compares counterfactual interventions under the same event conditions.

Current reference case:

> 2023 Osong Underpass Flood - Miho River and Gungpyeong 2 Underpass

Core question:

> What happened during the Osong flood, and how might the situation have changed if a different intervention had been applied?

## Current MVP

FloodOps 1.0 is a Historical Disaster Reconstruction Digital Twin MVP.

```text
KMA observed rainfall
-> HRFCO observed water level
-> official incident timeline
-> levee / overflow / breach events
-> Gungpyeong 2 underpass risk state
-> counterfactual intervention
-> baseline versus scenario comparison
```

Spatial context is provided by WAMIS rivers, SGIS boundary data, Copernicus DEM, official GIS Building Integrated Information, OSM historical snapshots, and local processed Osong layers.

The current `approx_flood_envelope` layer is a temporary DEM-constrained derived approximation. It is used to visualize a time-changing historical reconstruction state. It is not official Flood Extent, measured flood depth, measured velocity, or a validated hydraulic simulation.

Exposure KPIs that require valid flood geometry remain `PENDING_FLOOD_EXTENT`.

## Agent and Scenario Layer

FloodOps exposes deterministic analysis tools behind a small Agent workflow. An
optional LLM planner only selects a registered workflow and extracts parameters;
it never invents analysis values. If the SDK or credential is unavailable, the
planner falls back to the deterministic planner.

Available analysis flows include:

- closure-timing what-if: compare hypothetical underpass closure times
- inflow-delay what-if: shift downstream milestones by an explicit assumption
- exposure inventory: count nearby buildings, roads, and facilities without claiming flood impact
- portfolio scenario: select building IDs, apply interventions, and compare priority risk before/after

Portfolio scenario example:

```http
POST /api/scenarios
```

```json
{
  "name": "Osong building response drill",
  "event_id": "osong-2023",
  "building_ids": [1, 2, 3],
  "interventions": ["flood_barrier", "evacuation_support"]
}
```

```http
POST /api/scenarios/1/run
```

The current portfolio runner is a temporary, rule-based decision-support
calculation based on the derived HAND-like envelope. It is not a calibrated
hydraulic model, official flood extent, damage-cost model, or casualty model.

## What You Can See

- Historical Replay of the 2023-07-15 Osong incident sequence
- observed rainfall and water-level context
- MapLibre spatial layers for AOI, rivers, roads, buildings, DEM context, underpass, and approximate envelope
- baseline versus intervention comparison
- provenance and limitation notes for observed, derived, temporary, and reference data
- Agent workflow planning with deterministic fallback
- building-level response scenario API
- optional dark control-room UI preview on the `ui/dark-console` branch

## Run Locally

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload --port 8033
```

Backend:

- API docs: http://localhost:8033/docs
- OpenAPI schema: http://localhost:8033/openapi.json
- health check: http://localhost:8033/health

The optional LLM planner works without a credential by using the deterministic
fallback. To enable LLM routing, set `ANTHROPIC_API_KEY` in the repository
`.env` file and check `GET /api/agent/planner-status`.

### Frontend

```powershell
npm install
npm run dev
```

Frontend:

- http://localhost:5173
- http://127.0.0.1:5173

로컬 실행 포트는 FloodOps backend `8033`, Vite `5173`으로 고정한다. 다른 프로세스가
해당 포트를 사용 중이면 Vite가 다른 포트로 이동하지 않고 시작 오류를 표시한다.

Backend를 별도 포트로 실행해야 하는 예외 상황에는:

```powershell
$env:VITE_API_BASE = "http://127.0.0.1:8001"
npm run dev
```

### Docker

```powershell
docker compose up --build
```

Default Docker services:

- frontend: http://localhost:8080
- backend: http://localhost:8000
- PostGIS: localhost:5432

## Tests

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests
npm run build
```

## Documentation

- [Project Plan](docs/PROJECT_PLAN.md)
- [Development Guide](docs/DEVELOPMENT_GUIDE.md)
- [Data Guide](docs/DATA_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decision Records](docs/DECISIONS.md)
- [Data Quality Issues](docs/data-quality.md)
- [Current TODO](TODO.md)
- [Data Folder Guide](data/README.md)

Dataset provenance and availability are tracked under `data/manifests/`.

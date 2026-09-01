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

## What You Can See

- Historical Replay of the 2023-07-15 Osong incident sequence
- observed rainfall and water-level context
- MapLibre spatial layers for AOI, rivers, roads, buildings, DEM context, underpass, and approximate envelope
- baseline versus intervention comparison
- provenance and limitation notes for observed, derived, temporary, and reference data

## Run Locally

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Backend:

- API docs: http://localhost:8000/docs
- health check: http://localhost:8000/health

### Frontend

```powershell
npm install
npm run dev
```

Frontend:

- http://localhost:5173

If the backend uses a different port:

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

# FloodOps

FloodOps는 홍수 범위와 피해 노출을 확인하고, 방재 개입에 따른 결과를 비교하는 Flood Decision Digital Twin 프로젝트다.

현재 대표 분석 사건은 `osong-2023`이며, 오송 2023 하천·교통시설 침수와 궁평2지하차도 분석을 중심으로 MVP를 구성한다.

## 실행

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### Frontend

```powershell
npm install
npm run dev
```

- Frontend: http://localhost:5173
- API 문서: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Docker

```powershell
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend: http://localhost:8000
- PostGIS: localhost:5432

현재 애플리케이션 API는 데모 인메모리 데이터를 사용한다. 실제 Repository와 Migration은 후속 개발 범위다.

## 문서

- [프로젝트 기획안](docs/PROJECT_PLAN.md)
- [개발 지침](docs/DEVELOPMENT_GUIDE.md)
- [데이터 지침](docs/DATA_GUIDE.md)
- [시스템 아키텍처](docs/ARCHITECTURE.md)
- [설계 결정 기록](docs/DECISIONS.md)
- [현재 작업 목록](TODO.md)
- [데이터 폴더 사용법](data/README.md)
- 데이터별 출처·상태·해시는 `data/manifests/`에서 관리한다.

## 테스트

테스트와 검증 범위는 [개발 지침](docs/DEVELOPMENT_GUIDE.md)을 기준으로 한다.

```powershell
$env:PYTHONPATH = "backend"
pytest backend/tests
npm run build
```

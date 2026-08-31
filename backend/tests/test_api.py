import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_osong_event_is_default():
    response = client.get("/api/events")
    assert response.status_code == 200
    events = response.json()
    assert events[0]["id"] == "osong-2023"
    assert events[0]["origin"] == "DERIVED"


def test_osong_layers_use_processed_files():
    response = client.get("/api/events/osong-2023/layers")
    assert response.status_code == 200
    layers = response.json()
    assert layers["aoi"]["feature_count"] == 1
    assert layers["aoi"]["source_type"] == "OFFICIAL_ADMIN_BOUNDARY"
    assert layers["aoi"]["snapshot"] == "2023"
    assert layers["buildings"]["feature_count"] > 0
    assert layers["buildings"]["source_type"] == "OFFICIAL_BUILDING_INTEGRATED_INFORMATION"
    assert layers["buildings"]["snapshot"] == "2023-07-12"
    assert layers["roads"]["feature_count"] > 0
    assert layers["waterways"]["feature_count"] == 8
    assert layers["waterways"]["source_type"] == "OFFICIAL_RIVER_NETWORK"
    assert layers["waterways"]["snapshot"] == "NOT RECORDED"
    assert layers["terrain"]["feature_count"] == 303
    assert layers["terrain"]["source_type"] == "DEM_TERRAIN_CONTEXT"
    assert layers["facilities"]["feature_count"] == 386
    assert layers["underpass"]["feature_count"] == 1
    assert layers["underpass"]["data"]["features"][0]["geometry"]["type"] == "MultiLineString"


def test_osong_layers_ignore_current_osm_for_incident_analysis():
    response = client.get("/api/events/osong-2023/layers?layer_year=2026")
    assert response.status_code == 200
    layers = response.json()
    assert layers["buildings"]["source_type"] == "OFFICIAL_BUILDING_INTEGRATED_INFORMATION"
    assert layers["buildings"]["snapshot"] == "2023-07-12"
    assert layers["waterways"]["source_type"] == "OFFICIAL_RIVER_NETWORK"
    assert layers["waterways"]["snapshot"] == "NOT RECORDED"
    assert layers["waterways"]["feature_count"] == 8
    assert layers["terrain"]["feature_count"] == 303
    assert layers["facilities"]["feature_count"] == 386


def test_osong_status_separates_source_types():
    response = client.get("/api/events/osong-2023/status")
    assert response.status_code == 200
    status = response.json()
    assert status["flood_extent"]["status"] == "TEMPORARY"
    assert status["safemap_floodmarks"]["status"] == "VERIFIED"
    assert status["safemap_floodmarks"]["source_type"] == "OFFICIAL_WMS_SNAPSHOT"
    assert status["safemap_floodmarks"]["data_vintage"] == "2024 collection"
    assert status["rainfall"]["source_type"] == "OBSERVATION"
    assert status["rainfall"]["status"] == "VERIFIED"
    assert status["water_level"]["source_type"] == "OBSERVATION"
    assert status["water_level"]["status"] == "VERIFIED"
    assert status["water_level"]["records"] == 1299
    assert status["population"]["status"] == "VERIFIED"
    assert status["dem"]["source_type"] == "DEM"
    assert status["dem"]["low_elevation_feature_count"] == 303


def test_osong_timeline_uses_kma_observations():
    response = client.get("/api/events/osong-2023/flood/timeline")
    assert response.status_code == 200
    observations = response.json()
    assert len(observations) == 144
    assert observations[0]["station_id"] == "327"
    assert observations[0]["origin"] == "VERIFIED"
    assert observations[0]["unit"] == "mm"


def test_osong_summary_does_not_calculate_exposure_without_flood_extent():
    response = client.get("/api/events/osong-2023/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["official_population"] is not None
    assert summary["building_count"] > 0
    assert summary["road_count"] > 0
    assert summary["waterway_count"] == 8
    assert summary["terrain_low_elevation_cells"] == 303
    assert summary["terrain_low_elevation_threshold_m"] == 30.03
    assert summary["rainfall_records"] == 144
    assert summary["rainfall_peak_mm_per_hour"] is not None
    assert summary["water_level_peak_m"] is not None
    assert summary["primary_water_level_peak_m"] is not None
    assert summary["underpass_available"] is True
    assert summary["safemap_floodmarks_available"] is True
    assert summary["exposed_population"] == "PENDING_FLOOD_EXTENT"
    assert summary["exposed_buildings"] == "PENDING_FLOOD_EXTENT"


def test_osong_safemap_wms_snapshot_serves_local_png():
    response = client.get("/api/events/osong-2023/flood/safemap-wms-snapshot.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_baseline_uses_pending_exposure_metrics():
    response = client.get("/api/scenarios/baseline?event_id=osong-2023")
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["event_id"] == "osong-2023"
    assert result["exposed_population"] == "PENDING_FLOOD_EXTENT"

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import osong_repository
from app.main import _layers_gzip, _layers_json, app


client = TestClient(app)
LAYERS_URL = "/api/events/osong-2023/layers"
AOI_PATH = osong_repository.OSONG_DIR / "osong_sgis_admin_boundary_2023.geojson"


@pytest.fixture
def uncached_osong_layers():
    osong_repository.get_osong_repository.cache_clear()
    _layers_json.cache_clear()
    _layers_gzip.cache_clear()
    yield
    osong_repository.get_osong_repository.cache_clear()
    _layers_json.cache_clear()
    _layers_gzip.cache_clear()


def test_missing_processed_layer_is_reported_without_hiding_other_layers(monkeypatch, uncached_osong_layers):
    original_exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda path: False if path == AOI_PATH else original_exists(path))

    response = client.get(LAYERS_URL)
    assert response.status_code == 200
    layers = response.json()
    assert layers["aoi"]["status"] == "UNAVAILABLE"
    assert layers["aoi"]["error_code"] == "MISSING_PROCESSED_FILE"
    assert layers["aoi"]["feature_count"] == 0
    assert layers["aoi"]["data"] == {"type": "FeatureCollection", "features": []}
    assert layers["buildings"]["feature_count"] > 0
    assert client.get("/api/events/osong-2023/status").json()["layers"]["aoi"]["error_code"] == "MISSING_PROCESSED_FILE"


def test_catalog_event_with_unavailable_dataset_has_explicit_status():
    assert client.get("/api/events/iksan-2024/status").json()["status"] == "UNAVAILABLE"
    response = client.get("/api/events/iksan-2024/layers")
    assert response.status_code == 200
    assert all(layer["status"] == "UNAVAILABLE" and layer["feature_count"] == 0 for layer in response.json().values())
    assert client.get("/api/events/not-a-case/layers").status_code == 404


@pytest.mark.parametrize("contents", ["{invalid json", json.dumps({"type": "FeatureCollection", "features": "invalid"})])
def test_malformed_processed_layer_is_reported_without_server_error(monkeypatch, uncached_osong_layers, contents):
    original_read_text = Path.read_text
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, *args, **kwargs: contents if path == AOI_PATH else original_read_text(path, *args, **kwargs),
    )

    response = client.get(LAYERS_URL)
    assert response.status_code == 200
    layer = response.json()["aoi"]
    assert layer["status"] == "UNAVAILABLE"
    assert layer["error_code"] == "MALFORMED_PROCESSED_FILE"
    assert layer["feature_count"] == 0
    assert layer["data"] == {"type": "FeatureCollection", "features": []}
    assert client.get("/api/events/osong-2023/status").json()["layers"]["aoi"]["error_code"] == "MALFORMED_PROCESSED_FILE"

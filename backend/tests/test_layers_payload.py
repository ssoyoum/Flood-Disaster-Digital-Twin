import gzip
import json

import httpx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
URL = "/api/events/osong-2023/layers?layer_year=2023"


def test_layers_are_served_pre_compressed_once():
    raw = client.get(URL, headers={"Accept-Encoding": "gzip"})
    assert raw.status_code == 200
    assert raw.headers["content-encoding"] == "gzip"
    # httpx decodes one gzip layer; a second layer would make this JSON parse fail.
    assert raw.json()["buildings"]["feature_count"] > 0


def test_layers_without_gzip_support_get_plain_json():
    response = client.get(URL, headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in response.headers
    assert json.loads(response.content)["roads"]["feature_count"] > 0


def test_layer_payload_keeps_ui_properties_and_drops_register_columns():
    raw = client.get(URL, headers={"Accept-Encoding": "gzip"})
    # The browser downloads the compressed body; before trimming it was about 4.0 MB.
    compressed = len(gzip.compress(raw.content, 6))
    assert compressed < 1_400_000
    layers = raw.json()
    building = layers["buildings"]["data"]["features"][0]
    assert "official_feature_id" in building["properties"]
    assert not {"A4", "A5", "A2"} & set(building["properties"])  # lot address and land codes stay server-side
    cell = next(f for f in layers["hand_reconstruction"]["data"]["features"] if f["geometry"]["type"] == "Polygon")
    assert {"stage_index", "hand_threshold_m"} <= set(cell["properties"])
    x, y = cell["geometry"]["coordinates"][0][0][:2]
    assert len(str(x).split(".")[1]) <= 5 and len(str(y).split(".")[1]) <= 5


def test_analysis_still_reads_full_building_attributes():
    from app.data import get_layers

    assert "A4" in get_layers("osong-2023")["buildings"]["data"]["features"][0]["properties"]


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

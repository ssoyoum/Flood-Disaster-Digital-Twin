"""Layer caches share one parsed copy and keep only the gzip payload."""

import gzip

from fastapi.testclient import TestClient

from app.data import get_layers, layers_view
from app.main import app


def test_view_is_shared_and_get_layers_is_a_private_copy():
    assert layers_view("pohang-2022") is layers_view("pohang-2022")
    copy = get_layers("pohang-2022")
    assert copy == layers_view("pohang-2022") and copy is not layers_view("pohang-2022")


def test_plain_and_gzip_layer_responses_carry_the_same_payload():
    client = TestClient(app)
    zipped = client.get("/api/events/pohang-2022/layers", headers={"accept-encoding": "gzip"})
    plain = client.get("/api/events/pohang-2022/layers", headers={"accept-encoding": "identity"})
    assert zipped.status_code == plain.status_code == 200
    assert zipped.json() == plain.json()
    assert plain.headers.get("content-encoding") is None


def test_osong_repository_is_parsed_once_whatever_layer_year_is_passed():
    from app import osong_repository

    osong_repository._osong_repository.cache_clear()
    first = osong_repository.get_osong_repository()
    for year in (2023, 2022, 2023):
        assert osong_repository.get_osong_repository(year) is first
    assert osong_repository._osong_repository.cache_info().misses == 1

"""Stage-by-stage map layers for the non-Osong cases.

Seoul reveals the official flood traces deepest-first once the 60-minute rainfall passes the design
target; Pohang and Andong-Uiseong carry a HAND-like envelope whose threshold follows the reported
order of events. Both are ordering assumptions and the API must say so.
"""

from collections import Counter

from fastapi.testclient import TestClient

from app.main import app
from app.seoul_repository import DESIGN_RAINFALL_MM_PER_HOUR, SEOUL_RECONSTRUCTION_EVENTS, get_seoul_layers, trace_reveal_rule
from app.timeline_cases import CASES, get_timeline_layers, get_timeline_reconstruction

client = TestClient(app)


def test_seoul_trace_reveal_waits_for_the_design_rainfall_then_goes_deepest_first():
    rule = trace_reveal_rule()
    assert [row["state"] for row in rule] == [event["state"] for event in SEOUL_RECONSTRUCTION_EVENTS]
    hidden = [row for row in rule if row["reveal_depth_m"] is None]
    shown = [row for row in rule if row["reveal_depth_m"] is not None]
    assert hidden and shown
    assert all(row["rainfall_60min_running_max_mm"] < DESIGN_RAINFALL_MM_PER_HOUR for row in hidden)
    assert all(row["rainfall_60min_running_max_mm"] >= DESIGN_RAINFALL_MM_PER_HOUR for row in shown)
    depths = [row["reveal_depth_m"] for row in shown]
    assert depths == sorted(depths, reverse=True) and depths[-1] == 0.0

    traces = get_seoul_layers()["flood_extent"]["data"]["features"]
    stages = Counter(feature["properties"]["reveal_stage"] for feature in traces)
    first_shown = shown[0]["stage_index"]
    assert min(stages) == first_shown
    assert max(stages) <= len(rule) - 1
    deepest = max(float(feature["properties"].get("flood_depth_m") or 0) for feature in traces)
    assert all(feature["properties"]["reveal_stage"] == first_shown for feature in traces if float(feature["properties"].get("flood_depth_m") or 0) >= deepest)


def test_seoul_api_exposes_reveal_stage_and_rule():
    layers = client.get("/api/events/seoul-2022/layers", params={"year": 2022}).json()
    assert all("reveal_stage" in feature["properties"] for feature in layers["flood_extent"]["data"]["features"][:50])
    reconstruction = client.get("/api/events/seoul-2022/reconstruction").json()
    assert reconstruction["trace_reveal"][0]["reveal_depth_m"] is None
    assert reconstruction["trace_reveal"][-1]["reveal_depth_m"] == 0.0
    assert any("deepest-first" in item for item in reconstruction["limitations"])


def test_pohang_hand_envelope_grows_from_the_reported_overflow_in_reported_order():
    layers = get_timeline_layers("pohang-2022")
    hand = layers["hand_reconstruction"]
    assert hand["status"] == "TEMPORARY" and hand["source_type"] == "DERIVED_APPROXIMATION"
    assert hand["feature_count"] > 0 and layers["terrain"]["feature_count"] > 0
    counts = Counter(feature["properties"]["state"] for feature in hand["data"]["features"])
    order = [event["state"] for event in CASES["pohang-2022"]["replay"]]
    assert counts.get("typhoon_landfall", 0) == 0 and counts.get("first_notice", 0) == 0
    series = [counts.get(state, 0) for state in order]
    assert series[2] > 0 and series == sorted(series)
    assert all(feature["properties"]["not_official_flood_extent"] for feature in hand["data"]["features"][:20])

    reconstruction = get_timeline_reconstruction("pohang-2022")
    meta = reconstruction["hand_reconstruction"]
    assert meta["stage_driver"] == "REPORTED_ORDER_ONLY"
    assert meta["stage_counts"]["parking_full"] >= meta["stage_counts"]["river_overflow"]
    assert any("HAND" in item for item in reconstruction["limitations"])
    assert any(item["status"] == "TEMPORARY" and "HAND" in item["source"] for item in reconstruction["provenance"])


def test_timeline_hand_layer_is_slimmed_but_keeps_stage_properties():
    payload = client.get("/api/events/pohang-2022/layers", params={"year": 2022}).json()
    feature = payload["hand_reconstruction"]["data"]["features"][0]
    assert {"stage_index", "state", "hand_m", "hand_threshold_m"} <= set(feature["properties"])
    assert "mean_elevation_m" not in feature["properties"]
    status = client.get("/api/events/pohang-2022/status").json()
    assert status["dem"]["status"] == "DERIVED"
    assert status["layers"]["hand_reconstruction"]["status"] == "TEMPORARY"


def test_andong_hand_envelope_rises_to_the_predicted_peak_then_recedes():
    layers = get_timeline_layers("andong-uiseong-2026")
    hand = layers["hand_reconstruction"]
    assert hand["status"] == "TEMPORARY" and hand["feature_count"] > 0
    counts = Counter(feature["properties"]["state"] for feature in hand["data"]["features"])
    order = [event["state"] for event in CASES["andong-uiseong-2026"]["replay"]]
    series = [counts.get(state, 0) for state in order]
    peak = order.index("predicted_warning_level")
    assert series[: peak + 1] == sorted(series[: peak + 1]) and series[0] > 0
    assert series[peak] > series[order.index("warning_lifted")] > series[order.index("national_landslide_alert")]
    meta = get_timeline_reconstruction("andong-uiseong-2026")["hand_reconstruction"]
    assert meta["stage_driver"] == "REPORTED_GAUGE_AND_ORDER"
    assert "구계리" in meta["stage_driver_basis"]


def test_seoul_hand_band_follows_the_rainfall_fraction():
    layers = get_seoul_layers()
    hand = layers["hand_reconstruction"]
    assert hand["status"] == "TEMPORARY" and hand["feature_count"] > 0 and layers["terrain"]["feature_count"] > 0
    counts = Counter(feature["properties"]["state"] for feature in hand["data"]["features"])
    series = [counts.get(event["state"], 0) for event in SEOUL_RECONSTRUCTION_EVENTS]
    assert series == sorted(series) and series[0] > 0 and series[-1] > series[0]
    reconstruction = client.get("/api/events/seoul-2022/reconstruction").json()
    assert reconstruction["hand_reconstruction"]["stage_driver"] == "RAINFALL_60MIN_RUNNING_MAX"
    assert any("14-16%" in item for item in reconstruction["limitations"])
    status = client.get("/api/events/seoul-2022/status").json()
    assert status["dem"]["status"] == "DERIVED"

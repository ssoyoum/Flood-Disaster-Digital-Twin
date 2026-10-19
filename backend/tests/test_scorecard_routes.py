from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_facility_scorecard_route_counts_the_reference_event():
    response = client.get("/api/twin/facilities/gungpyeong2-underpass/scorecard")
    assert response.status_code == 200
    body = response.json()
    assert body["facility_id"] == "gungpyeong2-underpass"
    assert body["scorecard"]["hit"] + body["scorecard"]["miss"] == 1
    assert body["limitations"]


def test_facility_scorecard_route_rejects_unknown_facility():
    assert client.get("/api/twin/facilities/nowhere/scorecard").status_code == 404


def test_flood_forecast_history_route_serves_both_summaries():
    response = client.get("/api/watch/flood-forecast-history")
    assert response.status_code == 200
    body = response.json()
    assert body["issuances"]["issuances"] == sum(body["issuances"]["by_year"].values())
    assert body["official_vs_observed"]["경보"]["issue_lead_over_crossing"]["median_min"] is not None


def test_backtest_points_are_opt_in():
    plain = client.get("/api/twin/facilities/gungpyeong2-underpass/backtest").json()
    assert "points" not in plain
    with_points = client.get("/api/twin/facilities/gungpyeong2-underpass/backtest?points=true").json()
    assert len(with_points["points"]) == with_points["series"]["records"]
    assert with_points["first_closure_review"] == plain["first_closure_review"]

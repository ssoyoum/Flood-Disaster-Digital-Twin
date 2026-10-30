from unittest.mock import Mock

from app import facility_risk as fr
from app import national_watch as nw


def test_refresh_without_credentials_never_sends_a_bulk_request(monkeypatch):
    monkeypatch.delenv("HRFCO_API_KEY", raising=False)
    state = nw._LiveState()
    monkeypatch.setattr(nw, "_LIVE", state)
    bulk = Mock(side_effect=AssertionError("No network in missing-key mode"))
    monkeypatch.setattr(nw, "_bulk", bulk)
    assert nw.refresh_live(force=True) is state
    bulk.assert_not_called()
    assert state.last_error == "HRFCO_API_KEY is not configured"
    assert not state.snapshots


def test_rain_totals_use_existing_rain_only_refresh(monkeypatch):
    monkeypatch.setattr(nw, "_LIVE", nw._LiveState())
    monkeypatch.setattr(fr, "_RAIN_HISTORY", {})
    full = Mock(side_effect=AssertionError("Rain must not refresh water and dams"))
    rain = Mock()
    monkeypatch.setattr(nw, "refresh_live", full)
    monkeypatch.setattr(nw, "refresh_live_rain", rain)
    assert fr._live_totals() == (None, {})
    full.assert_not_called()
    rain.assert_called_once_with()


def test_configured_live_refresh_still_calls_the_feed(monkeypatch):
    monkeypatch.setenv("HRFCO_API_KEY", "offline-test-key")
    monkeypatch.setattr(nw, "_LIVE", nw._LiveState())
    bulk = Mock(return_value=[])
    monkeypatch.setattr(nw, "_bulk", bulk)
    nw.refresh_live(force=True)
    assert bulk.called
    assert all(call.args[0] == "offline-test-key" for call in bulk.call_args_list)


def test_missing_live_rain_preserves_real_replay_facility_evidence_without_http(monkeypatch):
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")
    monkeypatch.delenv("HRFCO_API_KEY", raising=False)
    monkeypatch.delenv("KMA_API_HUB_KEY", raising=False)
    monkeypatch.setattr(nw, "_LIVE", nw._LiveState())
    monkeypatch.setattr(fr, "_RAIN_HISTORY", {})
    bulk = Mock(side_effect=AssertionError("External bulk request is forbidden"))
    monkeypatch.setattr(nw, "_bulk", bulk)
    result = fr.facility_risk(rain_mode="live", limit=2000)
    assert result["mode"] == "replay" and result["rain_at"] is None
    assert result["counts"]["total"] > 0
    assert any(row["facility_id"] == "gungpyeong2-underpass" for row in result["facilities"])
    bulk.assert_not_called()

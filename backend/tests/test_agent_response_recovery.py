"""The Agent recovers when Gemini briefly returns an unusable decision."""

import json

import httpx

from app import agent_runner


def test_gemini_action_retries_one_malformed_decision(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(agent_runner, "llm_planner_status", lambda: {"available": True})
    responses = iter([
        httpx.Response(200, json={"candidates": []}),
        httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({"action": "final", "answer": "확인했습니다."})}]}}]}),
    ])
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return next(responses)

    monkeypatch.setattr(agent_runner.httpx, "post", fake_post)
    action = agent_runner._gemini_action({"question": "diagnostic"})

    assert action.action == "final"
    assert len(calls) == 2
    assert calls[0][1]["json"] == calls[1][1]["json"]

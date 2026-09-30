import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import llm_planner
from app.rate_limit import agent_limiter


@pytest.fixture(autouse=True)
def _no_real_llm_credentials(monkeypatch):
    """Keep a developer's local `.env` key from sending tests to the real Gemini API."""

    monkeypatch.setattr(llm_planner, "_env_file_loaded", True)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)


@pytest.fixture(autouse=True)
def _generous_agent_limits(monkeypatch):
    """Tests call the agent many times; the rate-limit test tightens these itself."""

    monkeypatch.setenv("FLOODOPS_AGENT_PER_MINUTE", "1000")
    monkeypatch.setenv("FLOODOPS_AGENT_PER_DAY", "1000")
    monkeypatch.setenv("FLOODOPS_AGENT_GLOBAL_PER_DAY", "1000")
    agent_limiter.reset()
    yield
    agent_limiter.reset()

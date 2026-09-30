import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import llm_planner


@pytest.fixture(autouse=True)
def _no_real_llm_credentials(monkeypatch):
    """Keep a developer's local `.env` key from sending tests to the real Gemini API."""

    monkeypatch.setattr(llm_planner, "_env_file_loaded", True)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)


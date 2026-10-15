"""Ollama provider: same loop and checks as Gemini, local endpoint, longer default budget."""

import json

import httpx
import pytest

from app import agent_runner
from app.schemas import AgentAskRequest


@pytest.fixture
def ollama(monkeypatch):
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    monkeypatch.delenv("AGENT_ASK_TIMEOUT_SECONDS", raising=False)
    sent = []

    def respond(*decisions):
        queue = iter(decisions)

        async def post(url, *, headers, json, timeout):
            sent.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            item = next(queue)
            return item if isinstance(item, httpx.Response) else httpx.Response(
                200, json={"message": {"content": item if isinstance(item, str) else _dumps(item)},
                           "prompt_eval_count": 3000, "eval_count": 80})

        monkeypatch.setattr(agent_runner, "_post_gemini", post)
        return sent

    return respond


def _dumps(value):
    return json.dumps(value, ensure_ascii=False)


def test_ollama_answers_through_the_same_loop_and_reports_tokens(ollama):
    sent = ollama({"action": "tool", "tool_name": "analyze_closure_timing", "parameters": {"closure_times": ["08:20"]}},
                  {"action": "final", "answer": "08:20 통제는 유입보다 7분 앞섭니다 [1].", "evidence_calls": [1]})
    result = agent_runner.ask_agent(AgentAskRequest(message="08:20에 통제했다면?"))
    assert result["status"] == "ANSWERED" and result["model"] == "ollama:qwen2.5:3b"
    assert result["diagnostics"]["tokens"] == {"prompt": 6000, "output": 160, "thoughts": 0, "total": 6160, "responses": 2}
    assert sent[0]["url"] == "http://localhost:11434/api/chat" and sent[0]["headers"] == {}
    assert sent[0]["json"]["options"]["num_ctx"] == agent_runner.DEFAULT_OLLAMA_NUM_CTX
    assert sent[0]["json"]["format"]["properties"]["action"]
    assert sent[0]["timeout"] == pytest.approx(agent_runner.DEFAULT_OLLAMA_ASK_TIMEOUT_SECONDS, abs=1)


def test_ollama_invalid_json_is_retried_once(ollama):
    ollama("not json", "still not json")
    result = agent_runner.ask_agent(AgentAskRequest(message="사건 정보를 알려줘"))
    codes = [failure["code"] for failure in result["diagnostics"]["failures"]]
    assert codes == ["model_invalid_decision", "model_invalid_decision"]
    assert result["diagnostics"]["model_requests"] == 2


def test_ollama_down_is_a_connection_failure_and_tools_still_answer(ollama, monkeypatch):
    async def refused(*args, **kwargs):
        raise httpx.ConnectError("refused")

    ollama()
    monkeypatch.setattr(agent_runner, "_post_gemini", refused)
    result = agent_runner.ask_agent(AgentAskRequest(message="08:20에 통제했다면?"))
    assert [failure["code"] for failure in result["diagnostics"]["failures"]] == ["model_connection_failed"]
    assert result["diagnostics"]["completion_source"] == "registered_tools"


def test_gemini_stays_the_default_provider(monkeypatch):
    monkeypatch.delenv("AGENT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("AGENT_ASK_TIMEOUT_SECONDS", raising=False)
    assert agent_runner.agent_llm_provider() == "gemini"
    assert agent_runner._ask_timeout_seconds() == agent_runner.DEFAULT_ASK_TIMEOUT_SECONDS

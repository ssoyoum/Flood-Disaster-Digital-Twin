"""In-memory request limits for endpoints that spend external LLM quota.

The public demo runs one uvicorn worker, so a process-local counter is enough.
Limits come from environment variables so the demo can be tightened without a
code change.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, default)))
    except ValueError:
        return default


class AgentRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._per_ip: dict[str, deque[float]] = {}
        self._all: deque[float] = deque()

    def reset(self) -> None:
        with self._lock:
            self._per_ip.clear()
            self._all.clear()

    def check(self, client: str) -> None:
        per_minute = _env_int("FLOODOPS_AGENT_PER_MINUTE", 6)
        per_day = _env_int("FLOODOPS_AGENT_PER_DAY", 60)
        global_per_day = _env_int("FLOODOPS_AGENT_GLOBAL_PER_DAY", 500)
        now = time.time()
        with self._lock:
            while self._all and now - self._all[0] > 86400:
                self._all.popleft()
            hits = self._per_ip.setdefault(client, deque())
            while hits and now - hits[0] > 86400:
                hits.popleft()
            recent = sum(1 for stamp in hits if now - stamp <= 60)
            if global_per_day and len(self._all) >= global_per_day:
                raise HTTPException(429, "오늘 Agent 질문 한도에 도달했습니다. 내일 다시 이용하거나 시나리오 비교 화면을 이용해 주세요.")
            if per_day and len(hits) >= per_day:
                raise HTTPException(429, "이 접속 주소의 오늘 Agent 질문 한도에 도달했습니다. 내일 다시 이용해 주세요.")
            if per_minute and recent >= per_minute:
                raise HTTPException(429, "질문이 너무 빠르게 이어지고 있습니다. 1분 뒤에 다시 질문해 주세요.")
            hits.append(now)
            self._all.append(now)


agent_limiter = AgentRateLimiter()


def client_key(request: Request) -> str:
    """Use the first X-Forwarded-For hop set by the reverse proxy, else the socket peer."""

    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

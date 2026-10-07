from __future__ import annotations

import asyncio
import time

import httpx

from .config import EngineConfig
from .metrics import Metrics, RequestSample
from .rate_limiter import RateLimiter


class Worker:
    def __init__(self, config: EngineConfig, client: httpx.AsyncClient, metrics: Metrics) -> None:
        self._config = config
        self._client = client
        self._metrics = metrics
        self._semaphore = asyncio.Semaphore(config.load.concurrency)
        self._limiter = RateLimiter(config.load.rate)

    async def _execute_one(self) -> None:
        async with self._semaphore:
            target = self._config.target
            start = time.perf_counter()
            try:
                response = await self._client.request(
                    target.method,
                    target.url,
                    headers=target.headers,
                    timeout=self._config.request.timeout,
                )
                latency_ms = (time.perf_counter() - start) * 1000
                self._metrics.record(RequestSample(latency_ms=latency_ms, status_code=response.status_code))
            except httpx.HTTPError as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                self._metrics.record(RequestSample(latency_ms=latency_ms, error=type(exc).__name__))

    async def run(self) -> None:
        deadline = time.monotonic() + self._config.load.duration
        pending: set[asyncio.Task] = set()
        try:
            while time.monotonic() < deadline:
                await self._limiter.acquire()
                if time.monotonic() >= deadline:
                    break
                task = asyncio.create_task(self._execute_one())
                pending.add(task)
                task.add_done_callback(pending.discard)
        finally:
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

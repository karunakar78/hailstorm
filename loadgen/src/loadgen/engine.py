from __future__ import annotations

import time

import httpx

from .config import EngineConfig
from .metrics import Metrics, Summary
from .worker import Worker


class LoadGenerator:
    def __init__(self, config: EngineConfig, client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._metrics = Metrics()
        self._client = client

    async def run(self) -> Summary:
        started = time.monotonic()
        if self._client is not None:
            worker = Worker(self._config, self._client, self._metrics)
            await worker.run()
        else:
            limits = httpx.Limits(
                max_connections=self._config.load.concurrency,
                max_keepalive_connections=self._config.load.concurrency,
            )
            async with httpx.AsyncClient(limits=limits) as client:
                worker = Worker(self._config, client, self._metrics)
                await worker.run()
        return self._metrics.summary(time.monotonic() - started)

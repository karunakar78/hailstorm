from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(self, rate: float, clock=time.monotonic) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self._interval = 1.0 / rate
        self._clock = clock
        self._start: float | None = None
        self._next_slot = 0.0

    async def acquire(self) -> None:
        if self._start is None:
            self._start = self._clock()
            self._next_slot = self._start
        wait_until = self._next_slot
        self._next_slot += self._interval
        delay = wait_until - self._clock()
        if delay > 0:
            await asyncio.sleep(delay)

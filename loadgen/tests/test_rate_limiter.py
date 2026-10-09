import time

import pytest

from loadgen.rate_limiter import RateLimiter


async def test_pacing_approximately_matches_rate():
    rate = 20.0
    limiter = RateLimiter(rate)
    start = time.monotonic()
    for _ in range(10):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    expected = 9 / rate  # 10 acquisitions => 9 intervals of wait
    assert elapsed == pytest.approx(expected, rel=0.35, abs=0.1)


def test_invalid_rate():
    with pytest.raises(ValueError):
        RateLimiter(0)

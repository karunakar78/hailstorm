import asyncio

import httpx
import pytest

from loadgen.config import EngineConfig, LoadConfig, TargetConfig
from loadgen.engine import LoadGenerator


def make_config(**load_overrides) -> EngineConfig:
    load = {"duration": 1, "rate": 10, "concurrency": 5, **load_overrides}
    return EngineConfig(target=TargetConfig(url="http://test/"), load=LoadConfig(**load))


async def test_engine_success():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    summary = await LoadGenerator(make_config(), client=client).run()
    await client.aclose()

    assert summary.total == 10
    assert summary.succeeded == 10
    assert summary.failed == 0
    assert summary.status_codes == {200: 10}
    assert calls == 10


async def test_engine_records_failures():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/fail":
            return httpx.Response(500)
        return httpx.Response(200)

    config = make_config()
    config.target.url = "http://test/fail"
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    summary = await LoadGenerator(config, client=client).run()
    await client.aclose()

    assert summary.total == 10
    assert summary.failed == 10
    assert summary.error_rate == 1.0
    assert summary.status_codes == {500: 10}


async def test_engine_records_http_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    summary = await LoadGenerator(make_config(rate=5, duration=1), client=client).run()
    await client.aclose()

    assert summary.total == 5
    assert summary.failed == 5
    assert summary.errors.get("ConnectError") == 5


async def test_concurrency_cap_respected():
    in_flight = 0
    max_in_flight = 0

    async def slow_handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(slow_handler))
    summary = await LoadGenerator(
        make_config(rate=20, duration=1, concurrency=3), client=client
    ).run()
    await client.aclose()

    assert max_in_flight <= 3
    assert summary.succeeded > 0

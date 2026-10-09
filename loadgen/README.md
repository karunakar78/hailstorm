# loadgen

A standalone, asyncio-based HTTP load-generation engine. It sends a configured number of requests per second against a target API for a configured duration, then prints a latency and success report.

## Overview

loadgen answers a narrow question: *what happens to my API when I send N requests per second for M seconds?* It is a single-process command-line engine, not a distributed load-testing platform. Configuration is a YAML file; results are printed to stdout as a text report.

The engine separates three concerns:

- **Scheduling** — a fixed-rate clock decides when requests are launched.
- **Execution** — a semaphore caps how many requests are in flight at once.
- **Observation** — every request becomes an immutable sample; metrics are aggregated once, after the run.

## Features

Implemented:

- YAML configuration validated with Pydantic before any traffic is generated
- Fixed-rate request pacing on a monotonic clock
- Configurable concurrency cap (maximum in-flight requests)
- Per-request timeout
- Per-request latency, status code, and error recording
- Summary report: totals, average RPS, error rate, average/p50/p95/p99 latency, status-code counts, error-type counts
- CLI (`loadgen` or `python -m loadgen`) and a small Python API
- Async test suite (pytest + pytest-asyncio) using httpx mock transports

Not implemented (planned / future):

- Distributed workers and test orchestration
- Request bodies (only method, URL, headers, and timeout are configurable)
- Retries, ramp-up, and graceful shutdown (signal handling)
- Live monitoring during a run; results are reported only at completion
- Persistent storage of results

## Technology stack

| Technology | Role |
|---|---|
| Python >= 3.11 | Runtime |
| asyncio | Concurrency model (single event loop) |
| httpx >= 0.28 | Async HTTP client; connection pool sized to concurrency |
| pydantic >= 2.0 | Configuration parsing and validation |
| PyYAML >= 6.0 | YAML config parsing |
| pytest, pytest-asyncio | Test framework (dev dependency) |

## Architecture

Request and data flow:

```text
config.yaml
  → load_config()                 # YAML → EngineConfig (Pydantic)
  → LoadGenerator.run()
      → httpx.AsyncClient         # shared client, pool limit = concurrency
      → Worker.run()
          → RateLimiter.acquire() # one slot every 1/rate seconds
          → asyncio.create_task(_execute_one)
              → semaphore         # at most `concurrency` in flight
              → client.request()  # HTTP request to target
              → Metrics.record()  # RequestSample(latency, status | error)
      → gather(pending)           # drain in-flight requests
  → Metrics.summary(elapsed)      # totals, RPS, percentiles
  → Summary.render()              # text report to stdout
```

Key units:

- `RateLimiter` controls launch cadence (rate).
- The `asyncio.Semaphore` plus the httpx connection pool cap in-flight requests (concurrency).
- `RequestSample` is the only data unit between the target and the report.

## Prerequisites

- Python 3.11 or newer
- pip

## Installation

From the repository root:

```bash
pip install -e "./loadgen[dev]"
```

or from inside `loadgen/`:

```bash
pip install -e ".[dev]"
```

The `dev` extra installs pytest and pytest-asyncio for the test suite.

## Configuration

The engine reads a YAML file (`--config` defaults to `config.yaml`):

```yaml
target:
  url: "http://localhost:8000/test"   # Target endpoint (required)
  method: "GET"                        # HTTP method (default: GET; uppercased)
  headers: {}                          # Optional request headers

load:
  duration: 30   # Test duration in seconds (required, > 0)
  rate: 10       # Target requests per second (required, > 0)
  concurrency: 5 # Max in-flight requests (required, >= 1)

request:
  timeout: 5     # Per-request timeout in seconds (default: 5.0)
```

The `request` section is optional; all of its fields have defaults.

Validation is fail-fast: invalid values (for example `duration <= 0`, `rate <= 0`, `concurrency < 1`) raise a `ValidationError` before any request is sent.

## Running

```bash
cd loadgen
loadgen --config config.yaml
```

or without the console script:

```bash
python -m loadgen --config config.yaml
```

The report is printed to stdout after the run:

```text
Duration:        2.1 s
Total requests:  20
Average RPS:     9.5
Successful:      20
Failed:          0
Error rate:      0.0%
Latency:
  avg:           7.2 ms
  p50:           4.7 ms
  p95:           18.0 ms
  p99:           42.1 ms
Status codes:
  200: 20
```

Note: the engine waits for in-flight requests to finish after the deadline, so the reported duration can slightly exceed the configured `duration`.

## Python API

```python
import asyncio
from loadgen import LoadGenerator, load_config

config = load_config("config.yaml")
summary = asyncio.run(LoadGenerator(config).run())
print(summary.render())
```

`LoadGenerator` also accepts an optional `httpx.AsyncClient` for dependency injection (used by the tests with `httpx.MockTransport`).

## Testing

```bash
cd loadgen
pytest
```

The suite uses `asyncio_mode = "auto"` (configured in `pyproject.toml`) and `httpx.MockTransport` to exercise the engine without network access. Last observed run: **12 passed** (pytest 9.1.1, pytest-asyncio 1.4.0, Python 3.12.6).

## Project structure

```text
loadgen/
├── config.yaml               # Example configuration
├── pyproject.toml            # Package metadata, dependencies, entry point, pytest config
├── src/loadgen/
│   ├── __init__.py           # Public API re-exports
│   ├── __main__.py           # python -m loadgen entry point
│   ├── cli.py                # argparse CLI (--config), runs engine, prints report
│   ├── config.py             # Pydantic config models and load_config()
│   ├── engine.py             # LoadGenerator: client setup, run, summary
│   ├── metrics.py            # RequestSample, Metrics, Summary, percentile calculation
│   ├── rate_limiter.py       # Fixed-rate slot scheduler
│   └── worker.py             # Scheduler loop, concurrency semaphore, request execution
└── tests/
    ├── test_config.py        # Config loading, defaults, validation
    ├── test_engine.py        # End-to-end runs against mock transports
    ├── test_metrics.py       # Aggregation and percentile math
    └── test_rate_limiter.py  # Pacing accuracy
```

## Design decisions

- **Fixed-rate scheduling, not a token bucket.** Each `acquire()` advances a slot counter by `1/rate` on a monotonic clock. If a slot is missed (busy event loop), the delay is clamped to zero, producing a short catch-up burst; this keeps the aggregate rate on schedule instead of silently under-shooting the target RPS.
- **Rate and concurrency are independent knobs.** Tasks are spawned at the configured rate regardless of response times; the semaphore (plus the httpx pool limit) is the actual in-flight cap. Raising `rate` without `concurrency` deepens the queue; raising `concurrency` lets the engine sustain the rate against a slower target.
- **One shared HTTP client.** A single `httpx.AsyncClient` with `max_connections` and `max_keepalive_connections` set to `concurrency`, so at most that many sockets exist at once.
- **Fail-fast validation.** Configuration is parsed and validated before any socket is opened.
- **Drain before reporting.** In-flight requests are awaited in a `finally` block, so the summary includes every launched request.
- **Errors are samples, not run failures.** Timeouts and connection errors are recorded as samples with the exception type; the run continues and there are no retries.
- **Aggregate at the end.** Samples accumulate in a lock-protected list and are summarized once, keeping the hot path simple.

## Known limitations

- Single-process, single machine; no distributed workers.
- All samples are held in memory until the run ends, which caps very long tests.
- No request body support; `target` accepts only `url`, `method`, and `headers`.
- No retries, ramp-up, or signal handling (interrupting the process does not produce a partial report).
- No live metrics during the run; the report is printed only at completion.
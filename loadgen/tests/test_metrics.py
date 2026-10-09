import pytest

from loadgen.metrics import Metrics, RequestSample


def test_summary_counts_and_success():
    metrics = Metrics()
    metrics.record(RequestSample(latency_ms=10.0, status_code=200))
    metrics.record(RequestSample(latency_ms=20.0, status_code=201))
    metrics.record(RequestSample(latency_ms=30.0, status_code=500))
    metrics.record(RequestSample(latency_ms=40.0, error="ReadTimeout"))

    summary = metrics.summary(duration_s=2.0)
    assert summary.total == 4
    assert summary.succeeded == 2
    assert summary.failed == 2
    assert summary.error_rate == 0.5
    assert summary.avg_rps == 2.0
    assert summary.latency_avg_ms == 25.0
    assert summary.status_codes == {200: 1, 201: 1, 500: 1}
    assert summary.errors == {"ReadTimeout": 1}


def test_percentile_calculation():
    metrics = Metrics()
    for i in range(1, 101):
        metrics.record(RequestSample(latency_ms=float(i), status_code=200))
    summary = metrics.summary(duration_s=1.0)
    assert summary.latency_p50_ms == pytest.approx(50.5)
    assert summary.latency_p95_ms == pytest.approx(95.05)
    assert summary.latency_p99_ms == pytest.approx(99.01)


def test_empty_summary():
    summary = Metrics().summary(duration_s=1.0)
    assert summary.total == 0
    assert summary.error_rate == 0.0
    assert summary.latency_p99_ms == 0.0

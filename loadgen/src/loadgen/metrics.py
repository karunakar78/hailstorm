from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass


@dataclass
class RequestSample:
    latency_ms: float
    status_code: int | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and self.status_code is not None and self.status_code < 400


@dataclass
class Summary:
    duration_s: float
    total: int
    succeeded: int
    failed: int
    error_rate: float
    avg_rps: float
    latency_avg_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    status_codes: dict[int, int]
    errors: dict[str, int]

    def render(self) -> str:
        lines = [
            f"Duration:        {self.duration_s:.1f} s",
            f"Total requests:  {self.total}",
            f"Average RPS:     {self.avg_rps:.1f}",
            f"Successful:      {self.succeeded}",
            f"Failed:          {self.failed}",
            f"Error rate:      {self.error_rate:.1%}",
            "Latency:",
            f"  avg:           {self.latency_avg_ms:.1f} ms",
            f"  p50:           {self.latency_p50_ms:.1f} ms",
            f"  p95:           {self.latency_p95_ms:.1f} ms",
            f"  p99:           {self.latency_p99_ms:.1f} ms",
        ]
        if self.status_codes:
            lines.append("Status codes:")
            for code, count in sorted(self.status_codes.items()):
                lines.append(f"  {code}: {count}")
        if self.errors:
            lines.append("Errors:")
            for err, count in sorted(self.errors.items()):
                lines.append(f"  {err}: {count}")
        return "\n".join(lines)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] + frac * (sorted_values[high] - sorted_values[low])


class Metrics:
    def __init__(self) -> None:
        self._samples: list[RequestSample] = []
        self._lock = threading.Lock()

    def record(self, sample: RequestSample) -> None:
        with self._lock:
            self._samples.append(sample)

    def summary(self, duration_s: float) -> Summary:
        with self._lock:
            samples = list(self._samples)
        total = len(samples)
        succeeded = sum(1 for s in samples if s.success)
        failed = total - succeeded
        latencies = sorted(s.latency_ms for s in samples)
        status_codes = Counter(s.status_code for s in samples if s.status_code is not None)
        errors = Counter(s.error for s in samples if s.error is not None)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        return Summary(
            duration_s=duration_s,
            total=total,
            succeeded=succeeded,
            failed=failed,
            error_rate=(failed / total) if total else 0.0,
            avg_rps=(total / duration_s) if duration_s > 0 else 0.0,
            latency_avg_ms=avg_latency,
            latency_p50_ms=_percentile(latencies, 50),
            latency_p95_ms=_percentile(latencies, 95),
            latency_p99_ms=_percentile(latencies, 99),
            status_codes=dict(status_codes),
            errors=dict(errors),
        )

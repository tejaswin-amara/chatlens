"""Benchmark for in-process Turbovec TurboQuant 4-bit vector search."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

try:
    import turbovec  # type: ignore[import-untyped]
except ImportError:
    turbovec = None


def run_turbovec_benchmark(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark in-process 4-bit TurboQuant vector search latency and throughput."""
    if turbovec is None:
        return {
            "mean_latency_us": 0.0,
            "p50_latency_us": 0.0,
            "p95_latency_us": 0.0,
            "p99_latency_us": 0.0,
            "throughput_ops_per_sec": 0.0,
            "available": False,
        }

    dim = 3072
    n_vectors = 50
    # Create index
    idx = turbovec.TurboQuantIndex(dim=dim, bit_width=4)
    np.random.seed(42)
    vectors = np.random.randn(n_vectors, dim).astype(np.float32)
    idx.add(vectors)

    query = np.random.randn(1, dim).astype(np.float32)

    latencies_us: list[float] = []

    # Warmup
    for _ in range(50):
        idx.search(query, k=3)

    t0 = time.perf_counter()
    for _ in range(iterations):
        start = time.perf_counter()
        idx.search(query, k=3)
        end = time.perf_counter()
        latencies_us.append((end - start) * 1_000_000.0)
    total_time = time.perf_counter() - t0

    latencies_us.sort()
    mean_lat = sum(latencies_us) / len(latencies_us)
    p50 = latencies_us[int(len(latencies_us) * 0.50)]
    p95 = latencies_us[int(len(latencies_us) * 0.95)]
    p99 = latencies_us[int(len(latencies_us) * 0.99)]
    throughput = iterations / total_time if total_time > 0 else 0.0

    return {
        "mean_latency_us": round(mean_lat, 2),
        "p50_latency_us": round(p50, 2),
        "p95_latency_us": round(p95, 2),
        "p99_latency_us": round(p99, 2),
        "throughput_ops_per_sec": round(throughput, 1),
        "available": True,
    }


if __name__ == "__main__":
    res = run_turbovec_benchmark(iterations=1000)
    print(
        f"Turbovec Benchmark: {res['mean_latency_us']} µs/op, "
        f"{res['throughput_ops_per_sec']:,.0f} ops/s"
    )

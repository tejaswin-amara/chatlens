"""Micro-benchmark for Tier-1 Regex Parser latency and throughput."""

import statistics
import time
from typing import Any

from src.parsing.regex_parser import RegexParser

SAMPLE_NOTICES = [
    "DSA class for section S11 shifted to H-005 for P3 today.",
    "Attention: ML lecture on 2026-10-16 period 4 will be conducted in HC-15C.",
    "OSSP Mid-term exam scheduled on 2026-10-22 at 09:00 AM in H-301A.",
    "ESD Final Lab Assessment submission deadline is 2026-11-05 23:59.",
    "University will remain closed tomorrow on account of Diwali festival.",
    "Holiday declared on 2026-10-20 due to municipal elections.",
    "DBSE P5 class cancelled today due to faculty meeting.",
    "Hey everyone, anyone have the notes from yesterday's Japanese class?",
    "Lunch meetup at the campus food court around 1:00 PM?",
    "Reminder: Submit your assignments before midnight.",
]


def run_parser_benchmark(iterations: int = 1000) -> dict[str, Any]:
    # Warm-up pass
    for msg in SAMPLE_NOTICES:
        RegexParser.parse(msg)

    latencies_us = []
    start_total = time.perf_counter_ns()

    for i in range(iterations):
        msg = SAMPLE_NOTICES[i % len(SAMPLE_NOTICES)]
        t0 = time.perf_counter_ns()
        RegexParser.parse(msg)
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1_000.0)

    total_time_ms = (time.perf_counter_ns() - start_total) / 1_000_000.0
    throughput = (iterations / total_time_ms) * 1000.0

    return {
        "iterations": iterations,
        "total_time_ms": round(total_time_ms, 2),
        "mean_latency_us": round(statistics.mean(latencies_us), 2),
        "median_latency_us": round(statistics.median(latencies_us), 2),
        "p99_latency_us": round(statistics.quantiles(latencies_us, n=100)[98], 2),
        "throughput_ops_per_sec": round(throughput, 1),
    }


if __name__ == "__main__":
    res = run_parser_benchmark()
    print("Parser Benchmark Results:")
    for k, v in res.items():
        print(f"  {k}: {v}")

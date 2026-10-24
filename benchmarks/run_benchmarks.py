"""Master runner for ChatLens ingestion, parser & latency optimization benchmarks."""

import sys

from benchmarks.benchmark_e2e_latency import (
    run_concurrent_sqlite_benchmark,
    run_streaming_ttft_benchmark,
    run_timetable_l1_cache_benchmark,
    run_today_e2e_benchmark,
)
from benchmarks.benchmark_parser import run_parser_benchmark
from benchmarks.benchmark_timetable import run_timetable_benchmark
from benchmarks.benchmark_turbovec import (
    run_simd_vector_benchmark,
    run_turbovec_benchmark,
)


def main() -> int:
    print("=" * 72)
    print("      ChatLens & SPARK PA Performance & Throughput Benchmark")
    print("=" * 72)

    print("\n[1/6] Running Tier-1 Regex Parser Benchmark (1,000 iterations)...")
    parser_res = run_parser_benchmark(iterations=1000)

    print("[2/6] Running Timetable Validation Benchmark (5,000 iterations)...")
    tt_res = run_timetable_benchmark(iterations=5000)

    print("[3/6] Running Timetable L1 Cache Benchmark (5,000 iterations)...")
    l1_res = run_timetable_l1_cache_benchmark(iterations=5000)

    print("[4/6] Running SIMD Contiguous Vector RAG Benchmark (1,000 iterations)...")
    simd_res = run_simd_vector_benchmark(iterations=1000)

    print("[5/6] Running Turbovec 4-Bit Vector RAG Benchmark (1,000 iterations)...")
    vec_res = run_turbovec_benchmark(iterations=1000)

    print("[6/6] Running End-to-End Latency & Concurrency Verification Gates...")
    today_res = run_today_e2e_benchmark(iterations=50)
    sqlite_res = run_concurrent_sqlite_benchmark(workers=16, writes_per_worker=15)
    ttft_res = run_streaming_ttft_benchmark(iterations=20)

    print("\n" + "-" * 72)
    print(f"{'Deterministic Route / Component':<34} | {'Mean Latency':<14} | {'Gate (<100µs)'}")
    print("-" * 72)

    p_pass = parser_res["mean_latency_us"] < 100.0
    tt_pass = tt_res["mean_latency_us"] < 100.0
    l1_pass = l1_res["mean_latency_us"] < 100.0
    simd_pass = simd_res["mean_latency_us"] < 100.0
    vec_pass = (not vec_res["available"]) or vec_res["mean_latency_us"] < 500.0

    print(
        f"{'Tier-1 Regex Parser':<34} | "
        f"{parser_res['mean_latency_us']:>8.2f} µs    | "
        f"{'PASS' if p_pass else 'FAIL'}"
    )
    print(
        f"{'Timetable Slot Validator':<34} | "
        f"{tt_res['mean_latency_us']:>8.2f} µs    | "
        f"{'PASS' if tt_pass else 'FAIL'}"
    )
    print(
        f"{'Timetable L1 Cache Lookup':<34} | "
        f"{l1_res['mean_latency_us']:>8.2f} µs    | "
        f"{'PASS' if l1_pass else 'FAIL'}"
    )
    print(
        f"{'SIMD Contiguous Vector RAG':<34} | "
        f"{simd_res['mean_latency_us']:>8.2f} µs    | "
        f"{'PASS' if simd_pass else 'FAIL'}"
    )
    print(
        f"{'Turbovec 4-Bit Vector RAG':<34} | "
        f"{vec_res['mean_latency_us']:>8.2f} µs    | "
        f"{'PASS' if vec_pass else 'FAIL'}"
    )

    print("\n" + "-" * 72)
    print(f"{'End-to-End System Gate':<34} | {'Measured Value':<14} | {'Acceptance Gate'}")
    print("-" * 72)

    today_pass = today_res["passed"]
    sqlite_pass = sqlite_res["passed"]
    ttft_pass = ttft_res["passed"]

    print(
        f"{'/today E2E Command Median':<34} | "
        f"{today_res['median_latency_ms']:>8.2f} ms    | "
        f"{'PASS (<25ms)' if today_pass else 'FAIL'}"
    )
    print(
        f"{'Concurrent SQLite Contention':<34} | "
        f"{sqlite_res['lock_contention_errors']:>8d} errs  | "
        f"{'PASS (0 errs)' if sqlite_pass else 'FAIL'}"
    )
    print(
        f"{'Gemini Stream TTFT (p95)':<34} | "
        f"{ttft_res['p95_ttft_ms']:>8.2f} ms    | "
        f"{'PASS (<500ms)' if ttft_pass else 'FAIL'}"
    )
    print("-" * 72)

    all_passed = (
        p_pass
        and tt_pass
        and l1_pass
        and simd_pass
        and vec_pass
        and today_pass
        and sqlite_pass
        and ttft_pass
    )

    if all_passed:
        print("\n✓ All performance, latency, and concurrency gates satisfied.")
        return 0
    else:
        print("\n❌ Performance regression detected.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

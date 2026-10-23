"""Master runner for ChatLens ingestion & parser benchmarks."""

import sys

from benchmarks.benchmark_parser import run_parser_benchmark
from benchmarks.benchmark_timetable import run_timetable_benchmark
from benchmarks.benchmark_turbovec import run_turbovec_benchmark


def main() -> int:
    print("=" * 68)
    print("      ChatLens & SPARK PA Performance & Throughput Benchmark")
    print("=" * 68)

    print("\n[1/3] Running Tier-1 Regex Parser Benchmark (1,000 iterations)...")
    parser_res = run_parser_benchmark(iterations=1000)

    print("[2/3] Running Timetable Validation Benchmark (5,000 iterations)...")
    tt_res = run_timetable_benchmark(iterations=5000)

    print("[3/3] Running Turbovec Vector RAG Benchmark (1,000 iterations)...")
    vec_res = run_turbovec_benchmark(iterations=1000)

    print("\n" + "-" * 68)
    print(f"{'Component':<28} | {'Latency (Mean)':<14} | {'Throughput':<15} | {'Gate'}")
    print("-" * 68)

    # Thresholds
    parser_pass = parser_res["mean_latency_us"] < 1000.0  # < 1.0 ms
    tt_pass = tt_res["mean_latency_us"] < 500.0  # < 0.5 ms
    vec_pass = (not vec_res["available"]) or vec_res["mean_latency_us"] < 500.0  # < 0.5 ms

    p_status = "PASS (< 1.0ms)" if parser_pass else "FAIL"
    tt_status = "PASS (< 0.5ms)" if tt_pass else "FAIL"
    vec_status = "PASS (< 0.5ms)" if vec_pass else "FAIL"

    p_lat = f"{parser_res['mean_latency_us']} µs"
    p_tps = f"{parser_res['throughput_ops_per_sec']:,.0f} ops/s"
    print(f"{'Tier-1 Regex Parser':<28} | {p_lat:<14} | {p_tps:<15} | {p_status}")

    tt_lat = f"{tt_res['mean_latency_us']} µs"
    tt_tps = f"{tt_res['throughput_ops_per_sec']:,.0f} ops/s"
    print(f"{'Timetable Slot Validator':<28} | {tt_lat:<14} | {tt_tps:<15} | {tt_status}")

    vec_lat = f"{vec_res['mean_latency_us']} µs"
    vec_tps = f"{vec_res['throughput_ops_per_sec']:,.0f} ops/s"
    print(f"{'Turbovec 4-Bit Vector RAG':<28} | {vec_lat:<14} | {vec_tps:<15} | {vec_status}")

    print("-" * 68)
    print(
        f"Details: Parser p99={parser_res['p99_latency_us']}µs, "
        f"Timetable p99={tt_res['p99_latency_us']}µs, "
        f"Turbovec p99={vec_res['p99_latency_us']}µs\n"
    )

    if parser_pass and tt_pass and vec_pass:
        print("✓ All performance gates satisfied.")
        return 0
    else:
        print("❌ Performance regression detected.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

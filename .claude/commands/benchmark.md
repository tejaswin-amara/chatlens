# Performance Benchmark Command (`/benchmark`)

Execute empirical latency and throughput benchmarks for message parsing and timetable resolution:

1. **Run Parser Benchmark**:
   ```bash
   uv run python benchmarks/run_benchmarks.py
   ```
2. **Review Metrics**:
   - Tier-1 Regex Parser latency: Target < 0.20ms per message.
   - Timetable Resolution latency: Target < 0.10ms per query.
   - Throughput: Target > 5,000 messages/sec.
   - Memory Stability: Zero memory leaks or unbounded cache growth.
3. **Compare**:
   Compare results against baseline thresholds and report performance score.

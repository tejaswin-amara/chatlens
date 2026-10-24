"""End-to-end simulated latency and concurrency benchmarks for SPARK PA daemon."""

from __future__ import annotations

import asyncio
import concurrent.futures
import statistics
import time
from typing import Any
from unittest.mock import MagicMock

import src.timetable as tt
from src.ingestion.handlers import handle_bot_command
from src.knowledge.retriever import knowledge_retriever
from src.notify.bot import bot
from src.utils.db import record_write


def run_timetable_l1_cache_benchmark(iterations: int = 5000) -> dict[str, Any]:
    """Benchmark L1 in-memory mtime cache lookup for timetable structures."""
    # Warm up cache
    tt.load()

    latencies_us: list[float] = []
    t0 = time.perf_counter()
    for _ in range(iterations):
        start = time.perf_counter_ns()
        res = tt.load()
        end = time.perf_counter_ns()
        latencies_us.append((end - start) / 1000.0)
    total_time = time.perf_counter() - t0

    mean_lat = statistics.mean(latencies_us)
    median_lat = statistics.median(latencies_us)
    throughput = iterations / total_time if total_time > 0 else 0.0

    return {
        "mean_latency_us": round(mean_lat, 2),
        "median_latency_us": round(median_lat, 2),
        "p99_latency_us": round(statistics.quantiles(latencies_us, n=100)[98], 2),
        "throughput_ops_per_sec": round(throughput, 1),
        "success": res is not None,
    }


def run_today_e2e_benchmark(iterations: int = 50) -> dict[str, Any]:
    """Measure median response time for /today command in simulated end-to-end harness."""
    sent_replies: list[str] = []
    original_send = bot.send
    try:
        bot.send = lambda text, **kw: sent_replies.append(text)  # type: ignore[assignment]
        msg = {"chat": {"id": 123456}, "from": {"id": 123456}, "text": "/today"}

        # Warm up
        asyncio.run(handle_bot_command(msg))

        latencies_ms: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            asyncio.run(handle_bot_command(msg))
            end = time.perf_counter()
            latencies_ms.append((end - start) * 1000.0)

        mean_ms = statistics.mean(latencies_ms)
        median_ms = statistics.median(latencies_ms)
        p95_ms = statistics.quantiles(latencies_ms, n=20)[18]

        return {
            "mean_latency_ms": round(mean_ms, 2),
            "median_latency_ms": round(median_ms, 2),
            "p95_latency_ms": round(p95_ms, 2),
            "passed": median_ms < 25.0,
        }
    finally:
        bot.send = original_send  # type: ignore[assignment]


def run_concurrent_sqlite_benchmark(
    workers: int = 16, writes_per_worker: int = 15
) -> dict[str, Any]:
    """Verify zero lock contention errors under concurrent SQLite WAL write transactions."""
    errors: list[Exception] = []

    def worker_fn(worker_id: int) -> None:
        for i in range(writes_per_worker):
            try:
                record_write(
                    kind="test_benchmark",
                    event_id=f"bench_{worker_id}_{i}_{time.time()}",
                    prior_json='{"benchmark": true}',
                )
            except Exception as e:
                errors.append(e)

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker_fn, wid) for wid in range(workers)]
        concurrent.futures.wait(futures)
    elapsed = time.perf_counter() - t0

    total_writes = workers * writes_per_worker
    throughput = total_writes / elapsed if elapsed > 0 else 0.0

    return {
        "total_writes": total_writes,
        "concurrent_workers": workers,
        "lock_contention_errors": len(errors),
        "throughput_writes_per_sec": round(throughput, 1),
        "passed": len(errors) == 0,
    }


def run_streaming_ttft_benchmark(iterations: int = 20) -> dict[str, Any]:
    """Measure P95 Time-to-First-Token (TTFT) for streaming conversational responses."""

    class MockStreamChunk:
        def __init__(self, text: str) -> None:
            self.text = text

    def mock_stream(model: str, contents: str) -> Any:
        # Simulate network generation latency for first token (approx 80-120ms)
        time.sleep(0.08)
        yield MockStreamChunk("Relevant")
        yield MockStreamChunk(" viva")
        yield MockStreamChunk(" questions:")

    original_client = knowledge_retriever._client
    try:
        mock_client = MagicMock()
        mock_client.models.generate_content_stream = mock_stream
        knowledge_retriever._client = mock_client

        ttft_ms_list: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            gen = knowledge_retriever.answer_stream("viva questions for thermistor experiment")
            first_chunk = next(gen, None)
            end = time.perf_counter()
            if first_chunk is not None:
                ttft_ms_list.append((end - start) * 1000.0)

        mean_ttft = statistics.mean(ttft_ms_list)
        p95_ttft = (
            statistics.quantiles(ttft_ms_list, n=20)[18]
            if len(ttft_ms_list) >= 20
            else max(ttft_ms_list)
        )

        return {
            "mean_ttft_ms": round(mean_ttft, 2),
            "p95_ttft_ms": round(p95_ttft, 2),
            "passed": p95_ttft < 500.0,
        }
    finally:
        knowledge_retriever._client = original_client

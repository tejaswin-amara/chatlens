"""Micro-benchmark for Timetable period parsing and slot validation."""

import statistics
import time
from datetime import date
from typing import Any

from src.parsing.schemas import ExtractedAcademicEvent
from src.timetable import Meta, Slot, Timetable, parse_periods, validate

PERIOD_EXPRESSIONS = [
    "P1",
    "P2",
    "P3-P4",
    "P5",
    "P7-P8",
    "P9",
    "Period 3",
    "Period 7",
    "08:10 - 09:00",
    "10:00 AM - 11:40 AM",
    "13:20 - 14:10",
]

MOCK_TIMETABLE = Timetable(
    meta=Meta(
        term="T04",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        sample=False,
    ),
    slots=[
        Slot(day="Mon", period=1, course="DSA", room="H-005", faculty="Dr. A"),
        Slot(day="Mon", period=2, course="DSA", room="H-005", faculty="Dr. A"),
        Slot(day="Tue", period=3, course="OSSP", room="HC-15C", faculty="Dr. B"),
        Slot(day="Tue", period=4, course="OSSP", room="HC-15C", faculty="Dr. B"),
        Slot(day="Wed", period=7, course="ML", room="H-301A", faculty="Dr. C"),
        Slot(day="Wed", period=8, course="ML", room="H-301A", faculty="Dr. C"),
        Slot(day="Thu", period=5, course="ESD", room="H107A", faculty="Dr. D"),
        Slot(day="Fri", period=9, course="DBSE", room="H006", faculty="Dr. E"),
    ],
)

SAMPLE_EVENTS = [
    ExtractedAcademicEvent(
        intent="ROOM_OVERRIDE",
        course_name="DSA",
        course_code="25CS2103E",
        room="H-006",
        target_date="2026-10-19",  # Monday
        period="P1-P2",
        summary="DSA shifted",
    ),
    ExtractedAcademicEvent(
        intent="ROOM_OVERRIDE",
        course_name="OSSP",
        course_code="25CS2104E",
        room="HC-16",
        target_date="2026-10-20",  # Tuesday
        period="P3-P4",
        summary="OSSP shifted",
    ),
    ExtractedAcademicEvent(
        intent="ROOM_OVERRIDE",
        course_name="ML",
        course_code="25SC2107E",
        room="H-302",
        target_date="2026-10-21",  # Wednesday
        period="P7-P8",
        summary="ML shifted",
    ),
]


def run_timetable_benchmark(iterations: int = 5000) -> dict[str, Any]:
    # Warm-up pass
    for expr in PERIOD_EXPRESSIONS:
        parse_periods(expr)
    for evt in SAMPLE_EVENTS:
        validate(evt, MOCK_TIMETABLE)

    latencies_us = []
    start_total = time.perf_counter_ns()

    for i in range(iterations):
        evt = SAMPLE_EVENTS[i % len(SAMPLE_EVENTS)]
        t0 = time.perf_counter_ns()
        validate(evt, MOCK_TIMETABLE)
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
    res = run_timetable_benchmark()
    print("Timetable Validation Benchmark Results:")
    for k, v in res.items():
        print(f"  {k}: {v}")

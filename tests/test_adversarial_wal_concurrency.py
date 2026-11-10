"""Adversarial stress test harness for Milestone M3: SQLite WAL State Machine & Concurrency.

Empirically verifies:
1. High-concurrency multi-threaded access across all 6 state tables without locks.
2. Recovery from uncommitted transactions, verifying zero locks and zero corruption.
3. chat_state monotonic ordering under randomized multi-threaded out-of-order updates.
4. llm_budget atomicity under high contention and multi-day rollover.
5. pending claim race conditions: 0 double claims under concurrent workers.
6. Concurrent readers during active write transactions (WAL non-blocking invariant).
"""

from __future__ import annotations

import concurrent.futures
import json
import random
import sqlite3
import threading
import time
from pathlib import Path

from src.utils.deduplication import MessageDeduplicator

# ==============================================================================
# CHALLENGE 1: High-Concurrency Multi-Thread Simulation across All 6 Tables
# ==============================================================================


def test_adversarial_wal_high_concurrency_stress(tmp_path):
    """Stress-test SQLite WAL under 20 concurrent threads executing mixed read/write operations."""
    db_file = str(tmp_path / "high_concurrency_stress.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    num_threads = 20
    ops_per_thread = 50
    errors: list[Exception] = []

    def worker_action(thread_idx: int) -> None:
        try:
            for i in range(ops_per_thread):
                op = (thread_idx + i) % 6
                if op == 0:
                    # Table 1: seen
                    msg_id = f"th_{thread_idx}_{i}"
                    dedup.mark_processed(chat_id=thread_idx, message_id=msg_id, content="test")
                    assert dedup.is_duplicate(chat_id=thread_idx, message_id=msg_id, content="test")
                elif op == 1:
                    # Table 2: chat_state
                    chat_id = 1000 + (thread_idx % 5)
                    dedup.update_chat_state(chat_id, last_id=i * 10)
                    state = dedup.get_chat_state(chat_id)
                    assert state is not None
                elif op == 2:
                    # Table 3: llm_budget
                    day = f"2026-11-{(thread_idx % 3) + 10:02d}"
                    calls = dedup.increment_llm_calls(day)
                    assert calls >= 1
                elif op == 3:
                    # Table 4: pending
                    event_payload = json.dumps({"thread": thread_idx, "iter": i})
                    pid = dedup.add_pending(event_payload)
                    assert pid > 0
                    if i % 2 == 0:
                        dedup.claim_pending(pid)
                        dedup.finish_pending(pid, "DONE")
                elif op == 4:
                    # Table 5: writes
                    dedup.record_write(
                        "insert", f"ev_{thread_idx}_{i}", json.dumps({"source": "cal"})
                    )
                    lw = dedup.last_write()
                    assert lw is not None
                elif op == 5:
                    # Table 6: meta
                    key = f"key_{thread_idx % 4}"
                    dedup.meta_set(key, str(time.time()))
                    val = dedup.meta_get(key)
                    assert val is not None
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker_action, args=(t,)) for t in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30.0)

    # Invariant: Zero exceptions raised across 1,000 operations
    assert len(errors) == 0, f"Encountered {len(errors)} concurrency errors: {errors[:5]}"

    # Invariant: Database journal mode is WAL and integrity check passes
    conn = sqlite3.connect(db_file)
    try:
        jm = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert jm.lower() == "wal", f"Journal mode regressed from WAL: {jm}"
        integrity = conn.execute("PRAGMA integrity_check;").fetchall()
        assert integrity == [("ok",)], f"Integrity check failed: {integrity}"
    finally:
        conn.close()


# ==============================================================================
# CHALLENGE 2: Uncommitted Transaction Abort & Crash Recovery
# ==============================================================================


def test_adversarial_uncommitted_transaction_and_crash_recovery(tmp_path):
    """Verify that uncommitted transactions and abrupt connection closes recover cleanly."""
    db_file = str(tmp_path / "crash_recovery.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    # Seed initial data
    dedup.meta_set("status", "initial")
    dedup.update_chat_state(chat_id=777, last_id=100)

    # 1. Open raw connection, begin EXCLUSIVE, write uncommitted changes, then close abruptly
    raw_conn = sqlite3.connect(db_file, timeout=1.0)
    raw_conn.execute("BEGIN EXCLUSIVE;")
    raw_conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('status', 'uncommitted_leak');"
    )
    raw_conn.execute("UPDATE chat_state SET last_id = 999 WHERE chat_id = 777;")
    # Abrupt close without COMMIT or ROLLBACK (simulating worker crash)
    raw_conn.close()

    # 2. Immediately attempt reading and writing via MessageDeduplicator
    # Must NOT fail with sqlite3.OperationalError: database is locked
    recovered_status = dedup.meta_get("status")
    recovered_last_id = dedup.get_chat_state(777)

    # Invariant: SQLite WAL rolled back uncommitted transaction
    assert recovered_status == "initial", f"Leaked uncommitted transaction: {recovered_status}"
    assert recovered_last_id == 100, f"Leaked uncommitted chat_state: {recovered_last_id}"

    # 3. Verify subsequent writes succeed immediately
    dedup.meta_set("status", "recovered_cleanly")
    assert dedup.meta_get("status") == "recovered_cleanly"

    # 4. Verify SQLite header integrity (first 16 bytes: 'SQLite format 3\x00')
    header = Path(db_file).read_bytes()[:16]
    assert header == b"SQLite format 3\x00", f"Corrupted SQLite header: {header}"

    # 5. Verify PRAGMA quick_check and integrity_check
    conn = sqlite3.connect(db_file)
    try:
        assert conn.execute("PRAGMA quick_check;").fetchall() == [("ok",)]
        assert conn.execute("PRAGMA integrity_check;").fetchall() == [("ok",)]
    finally:
        conn.close()


# ==============================================================================
# CHALLENGE 3: Non-Blocking Concurrent Readers During Active Write Transaction
# ==============================================================================


def test_adversarial_concurrent_readers_during_active_write_transaction(tmp_path):
    """Verify WAL invariant: active write transaction does NOT block concurrent readers."""
    db_file = str(tmp_path / "readers_during_writer.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    dedup.meta_set("heartbeat", "1000.0")

    write_started = threading.Event()
    read_completed = threading.Event()
    reader_results: list[str | None] = []
    reader_errors: list[Exception] = []

    def writer():
        conn = sqlite3.connect(db_file, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('heartbeat', '2000.0');")
        write_started.set()
        # Hold transaction open for 0.5s while readers execute
        time.sleep(0.5)
        conn.execute("COMMIT;")
        conn.close()

    def reader():
        try:
            write_started.wait(timeout=5.0)
            # Reader executes while writer transaction is held open
            val = dedup.meta_get("heartbeat")
            reader_results.append(val)
        except Exception as e:
            reader_errors.append(e)
        finally:
            read_completed.set()

    w_thread = threading.Thread(target=writer)
    r_threads = [threading.Thread(target=reader) for _ in range(5)]

    w_thread.start()
    for r in r_threads:
        r.start()

    for r in r_threads:
        r.join(timeout=5.0)
    w_thread.join(timeout=5.0)

    # Invariant: Readers were never blocked by the active write transaction
    assert len(reader_errors) == 0, f"Readers failed with errors: {reader_errors}"
    # Invariant: Readers read pre-commit snapshot ('1000.0') cleanly
    for res in reader_results:
        assert res == "1000.0", f"Reader saw uncommitted or invalid state: {res}"

    # Invariant: After commit, readers see updated value
    assert dedup.meta_get("heartbeat") == "2000.0"


# ==============================================================================
# CHALLENGE 4: chat_state Monotonic Ordering Under Randomized Concurrency
# ==============================================================================


def test_adversarial_chat_state_monotonic_ordering_race(tmp_path):
    """Verify that out-of-order update_chat_state NEVER regresses last_id, even under heavy race."""
    db_file = str(tmp_path / "chat_state_race.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    chat_id = 99999
    # Create sequence 1..200 and shuffle completely
    ids = list(range(1, 201))
    random.seed(42)
    shuffled_ids = ids[:]
    random.shuffle(shuffled_ids)

    observed_history: list[int] = []
    monotonicity_violations: list[tuple[int, int]] = []
    stop_observing = threading.Event()

    def observer():
        last_seen = 0
        while not stop_observing.is_set():
            current = dedup.get_chat_state(chat_id)
            if current is not None:
                if current < last_seen:
                    monotonicity_violations.append((last_seen, current))
                last_seen = current
                observed_history.append(current)
            time.sleep(0.001)

    obs_thread = threading.Thread(target=observer)
    obs_thread.start()

    # Partition shuffled IDs across 10 concurrent updater threads
    def updater(sub_ids: list[int]):
        for mid in sub_ids:
            dedup.update_chat_state(chat_id, mid)

    chunk_size = 20
    chunks = [shuffled_ids[i : i + chunk_size] for i in range(0, len(shuffled_ids), chunk_size)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(updater, chunks))

    stop_observing.set()
    obs_thread.join(timeout=5.0)

    # Invariant 1: No monotonicity violations observed at any point during concurrent updates
    assert len(monotonicity_violations) == 0, (
        f"Monotonicity violated during race: {monotonicity_violations}"
    )

    # Invariant 2: Final state must be the global maximum (200)
    final_id = dedup.get_chat_state(chat_id)
    assert final_id == 200, f"Expected final last_id=200, got {final_id}"

    # Invariant 3: Subsequent out-of-order updates with lower IDs NEVER decrement last_id
    dedup.update_chat_state(chat_id, 1)
    assert dedup.get_chat_state(chat_id) == 200
    dedup.update_chat_state(chat_id, 150)
    assert dedup.get_chat_state(chat_id) == 200
    dedup.update_chat_state(chat_id, 199)
    assert dedup.get_chat_state(chat_id) == 200
    # Higher ID advances it
    dedup.update_chat_state(chat_id, 201)
    assert dedup.get_chat_state(chat_id) == 201


# ==============================================================================
# CHALLENGE 5: llm_budget Concurrency Atomicity & Multi-Day Rollover
# ==============================================================================


def test_adversarial_llm_budget_atomic_increments(tmp_path):
    """Verify that concurrent increments to llm_budget suffer 0 lost updates."""
    db_file = str(tmp_path / "llm_budget_race.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    day = "2026-11-10"
    num_threads = 10
    increments_per_thread = 20
    total_expected = num_threads * increments_per_thread

    def worker():
        for _ in range(increments_per_thread):
            dedup.increment_llm_calls(day)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        for f in futures:
            f.result()

    # Invariant: Zero lost updates
    final_calls = dedup.get_llm_calls(day)
    assert final_calls == total_expected, (
        f"Lost update anomaly: expected {total_expected}, got {final_calls}"
    )


def test_adversarial_llm_budget_daily_rollover(tmp_path):
    """Verify multi-day budget isolation and seamless midnight rollover."""
    db_file = str(tmp_path / "llm_budget_rollover.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    days = ["2026-11-08", "2026-11-09", "2026-11-10", "2026-11-11"]

    for idx, d in enumerate(days):
        expected_calls = (idx + 1) * 7
        for _ in range(expected_calls):
            dedup.increment_llm_calls(d)

    # Invariant: Each day retains its exact count without cross-talk
    assert dedup.get_llm_calls("2026-11-08") == 7
    assert dedup.get_llm_calls("2026-11-09") == 14
    assert dedup.get_llm_calls("2026-11-10") == 21
    assert dedup.get_llm_calls("2026-11-11") == 28

    # Unseen day defaults to 0
    assert dedup.get_llm_calls("2026-11-12") == 0


# ==============================================================================
# CHALLENGE 6: Pending Queue Claim Race (Zero Double-Claims)
# ==============================================================================


def test_adversarial_pending_claim_concurrency_race(tmp_path):
    """Verify that concurrent workers competing for pending items NEVER double-claim an event."""
    db_file = str(tmp_path / "pending_race.db")
    dedup = MessageDeduplicator(db_path=db_file)
    dedup._init_db()

    num_items = 50
    pids = [
        dedup.add_pending(json.dumps({"intent": "ROOM_OVERRIDE", "item": i}))
        for i in range(num_items)
    ]
    assert len(pids) == num_items

    claimed_by_thread: dict[int, list[int]] = {t: [] for t in range(10)}
    lock = threading.Lock()

    def worker(worker_id: int):
        for pid in pids:
            if dedup.claim_pending(pid):
                with lock:
                    claimed_by_thread[worker_id].append(pid)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, w) for w in range(10)]
        for f in futures:
            f.result()

    # Invariant 1: Total claimed events must exactly equal total inserted events
    all_claimed = []
    for claims in claimed_by_thread.values():
        all_claimed.extend(claims)
    assert len(all_claimed) == num_items, (
        f"Expected {num_items} claimed events, got {len(all_claimed)}"
    )

    # Invariant 2: Exactly zero double-claims (disjoint sets)
    assert len(set(all_claimed)) == num_items, "Detected double claim across worker threads!"

    # Invariant 3: list_pending returns empty list
    assert len(dedup.list_pending()) == 0

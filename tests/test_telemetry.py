import asyncio
import time
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.telemetry.emitter import TelemetryEmitter
from src.telemetry.schemas import TimetableAccessEvent


@pytest.fixture
def test_emitter():
    emitter = TelemetryEmitter()
    settings.telemetry_url = "http://test.local/telemetry"
    return emitter


def test_emit_queues_event(test_emitter):
    event: TimetableAccessEvent = {
        "event_id": "test-1",
        "user_id": "user123",
        "course_code": "CS101",
        "period": 1,
        "day": "Monday",
        "status": "success",
        "latency_ms": 42.5,
        "timestamp": time.time(),
    }

    test_emitter.emit(event)
    assert test_emitter.queue.qsize() == 1
    assert test_emitter.queue.get_nowait() == event


def test_emit_drops_when_queue_full(test_emitter):
    for i in range(1000):
        test_emitter.queue.put_nowait({"id": i})

    test_emitter.emit({"id": 1001})
    assert test_emitter.queue.qsize() == 1000


@pytest.mark.asyncio
async def test_worker_processes_event_success(test_emitter):
    event = {"test": "event"}
    test_emitter.queue.put_nowait(event)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        test_emitter.start()
        await asyncio.sleep(0.1)

        await test_emitter.stop()

    mock_urlopen.assert_called_once()
    req = mock_urlopen.call_args[0][0]
    assert req.get_full_url() == "http://test.local/telemetry"
    assert req.data == b'{"test": "event"}'
    assert req.get_header("Content-type") == "application/x-ndjson"
    assert test_emitter.consecutive_errors == 0


@pytest.mark.asyncio
async def test_worker_circuit_breaker(test_emitter):
    settings.circuit_breaker_error_threshold = 2
    settings.circuit_breaker_cooldown_seconds = 60

    event1 = {"test": 1}
    event2 = {"test": 2}
    event3 = {"test": 3}

    test_emitter.queue.put_nowait(event1)
    test_emitter.queue.put_nowait(event2)
    test_emitter.queue.put_nowait(event3)

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("test error")

        test_emitter.start()
        await asyncio.sleep(0.2)

        await test_emitter.stop()

    assert mock_urlopen.call_count == 2
    assert test_emitter.consecutive_errors == 2
    assert test_emitter.circuit_open_until > time.time()

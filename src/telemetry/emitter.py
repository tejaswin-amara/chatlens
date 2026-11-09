import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)


class TelemetryEmitter:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self.worker_task: asyncio.Task[None] | None = None
        self.consecutive_errors: int = 0
        self.circuit_open_until: float = 0.0

    def start(self) -> None:
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        if self.worker_task is not None:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None

    def emit(self, event: dict[str, Any]) -> None:
        if not settings.telemetry_url:
            return

        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Telemetry queue full, dropping event.")

    async def _worker(self) -> None:
        while True:
            try:
                event = await self.queue.get()
                await self._process_event(event)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telemetry worker: {e}")

    async def _process_event(self, event: dict[str, Any]) -> None:
        now = time.time()
        if now < self.circuit_open_until:
            return  # Circuit is open, drop event

        payload = json.dumps(event).encode("utf-8")

        url = settings.telemetry_url
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return

        headers = {"Content-Type": "application/x-ndjson"}
        if settings.telemetry_token:
            headers["Authorization"] = f"Bearer {settings.telemetry_token.get_secret_value()}"

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")  # noqa: S310

        def send_request() -> None:
            with urllib.request.urlopen(req, timeout=5) as response:  # noqa: S310
                response.read()

        try:
            await asyncio.to_thread(send_request)
            self.consecutive_errors = 0
        except Exception as e:
            self.consecutive_errors += 1
            if self.consecutive_errors >= settings.circuit_breaker_error_threshold:
                self.circuit_open_until = time.time() + settings.circuit_breaker_cooldown_seconds
                logger.warning(
                    f"Telemetry circuit broken after {self.consecutive_errors} errors. "
                    f"Pausing for {settings.circuit_breaker_cooldown_seconds}s. Last error: {e}"
                )


emitter = TelemetryEmitter()

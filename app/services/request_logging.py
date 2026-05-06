from __future__ import annotations

from datetime import UTC, datetime
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any

from app.db import session as db_session
from app.db.models import ApiRequestLog


_STOP = object()


class RequestLogWriter:
    def __init__(self, *, batch_size: int = 100, flush_interval: float = 1.0, queue_size: int = 5000) -> None:
        self.batch_size = max(1, batch_size)
        self.flush_interval = max(0.2, flush_interval)
        self._queue: Queue[dict[str, Any] | object] = Queue(maxsize=max(100, queue_size))
        self._thread: Thread | None = None
        self._lock = Lock()
        self._stop_event = Event()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = Thread(target=self._run, name="request-log-writer", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            self._stop_event.set()
            try:
                self._queue.put(_STOP, timeout=max(min(timeout, 1.0), 0.1))
            except Full:
                pass
            self._thread = None
        thread.join(timeout=timeout)

    def enqueue(self, *, request_id: str, method: str, path: str, status_code: int, duration_ms: float, user_id: int | None) -> bool:
        now = datetime.now(UTC)
        payload = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": int(status_code),
            "duration_ms": float(duration_ms),
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }
        try:
            self._queue.put_nowait(payload)
        except Full:
            return False
        return True

    def _flush(self, batch: list[dict[str, Any]]) -> None:
        if not batch:
            return
        try:
            with db_session.SessionLocal() as db:
                db.bulk_insert_mappings(ApiRequestLog, batch)
                db.commit()
        except Exception:
            return

    def _run(self) -> None:
        batch: list[dict[str, Any]] = []
        deadline = monotonic() + self.flush_interval
        while True:
            timeout = max(0.0, deadline - monotonic()) if batch else self.flush_interval
            try:
                item = self._queue.get(timeout=timeout)
            except Empty:
                item = None
            if item is _STOP:
                self._flush(batch)
                return
            if item is None:
                if batch:
                    self._flush(batch)
                    batch = []
                if self._stop_event.is_set() and self._queue.empty():
                    return
                deadline = monotonic() + self.flush_interval
                continue
            batch.append(item)
            if len(batch) >= self.batch_size:
                self._flush(batch)
                batch = []
                if self._stop_event.is_set() and self._queue.empty():
                    return
                deadline = monotonic() + self.flush_interval
                continue
            if monotonic() >= deadline:
                self._flush(batch)
                batch = []
                if self._stop_event.is_set() and self._queue.empty():
                    return
                deadline = monotonic() + self.flush_interval


request_log_writer = RequestLogWriter()

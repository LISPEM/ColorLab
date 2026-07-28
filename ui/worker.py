"""Background worker that runs the ColorLab pipeline off the UI thread."""

from __future__ import annotations

import queue
import threading
from typing import Optional

from dataManager.loadfiles4CIE import (
    NoValidDataError,
    ProcessingParams,
    process_batch,
)


EVENT_PROGRESS = "progress"     # (EVENT_PROGRESS, i, total, filename)
EVENT_FILE_ERROR = "file_error"  # (EVENT_FILE_ERROR, filename, reason)
EVENT_DONE = "done"             # (EVENT_DONE, figure)
EVENT_FATAL = "fatal"           # (EVENT_FATAL, message)
EVENT_CANCELLED = "cancelled"   # (EVENT_CANCELLED,)


class ProcessingWorker:
    """Spawns a daemon thread and streams events back via a queue."""

    def __init__(self, event_queue: "queue.Queue[tuple]") -> None:
        self._queue = event_queue
        self._thread: Optional[threading.Thread] = None
        self._cancel = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, params: ProcessingParams) -> None:
        if self.is_running:
            return
        self._cancel.clear()
        self._thread = threading.Thread(
            target=self._run, args=(params,), daemon=True
        )
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def _run(self, params: ProcessingParams) -> None:
        try:
            figure = process_batch(
                params,
                on_progress=lambda i, total, name: self._queue.put(
                    (EVENT_PROGRESS, i, total, name)
                ),
                on_file_error=lambda name, reason: self._queue.put(
                    (EVENT_FILE_ERROR, name, reason)
                ),
                should_cancel=self._cancel.is_set,
            )
        except NoValidDataError as exc:
            self._queue.put((EVENT_FATAL, str(exc)))
            return
        except FileNotFoundError as exc:
            self._queue.put((EVENT_FATAL, f"Folder not found: {exc}"))
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._queue.put((EVENT_FATAL, f"{exc.__class__.__name__}: {exc}"))
            return

        if self._cancel.is_set():
            self._queue.put((EVENT_CANCELLED,))
        else:
            self._queue.put((EVENT_DONE, figure))

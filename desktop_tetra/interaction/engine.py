from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from .livefeed import LiveFeed


class LiveEngine:
    _instance: Optional["LiveEngine"] = None
    _lock = threading.RLock()

    def __init__(self, monitor_index: int = 1, target_fps: int = 4) -> None:
        self.feed = LiveFeed(monitor_index=monitor_index, target_fps=target_fps)
        self._running = False

    @classmethod
    def instance(cls, monitor_index: int = 1, target_fps: int = 4) -> "LiveEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = LiveEngine(monitor_index=monitor_index, target_fps=target_fps)
            return cls._instance

    def start(self) -> None:
        if self._running:
            return
        self.feed.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        self.feed.stop()
        self._running = False

    def snapshot(self) -> Dict[str, Any]:
        return self.feed.snapshot()

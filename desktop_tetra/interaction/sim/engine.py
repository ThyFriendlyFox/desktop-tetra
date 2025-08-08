from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from ..crdt import CRDTStore


class SimEngine:
    _instance: Optional["SimEngine"] = None
    _lock = threading.RLock()

    def __init__(self, tick_hz: int = 4, seed: int = 0) -> None:
        self.store = CRDTStore()
        self.tick_hz = max(1, tick_hz)
        self.seed = seed
        self._stop = threading.Event()
        self._thr: Optional[threading.Thread] = None
        self._running = False

    @classmethod
    def instance(cls, tick_hz: int = 4, seed: int = 0) -> "SimEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = SimEngine(tick_hz=tick_hz, seed=seed)
            return cls._instance

    @classmethod
    def instance_if_running(cls) -> Optional["SimEngine"]:
        with cls._lock:
            return cls._instance if cls._instance and cls._instance._running else None

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self._thr.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        self._stop.set()
        if self._thr:
            self._thr.join(timeout=2)
        self._running = False

    def _run(self) -> None:
        period = 1.0 / float(self.tick_hz)
        # Seed a simple world: a window with a button and a status text
        now = time.time()
        self.store.upsert_node({
            "id": "win:main", "role": "Window", "title": "SimApp", "frame": {"x": 100, "y": 100, "w": 800, "h": 600}, "ts": now
        })
        self.store.upsert_node({
            "id": "btn:new", "role": "Button", "title": "New", "frame": {"x": 140, "y": 180, "w": 120, "h": 36}, "ts": now
        })
        self.store.upsert_node({
            "id": "txt:status", "role": "StaticText", "title": "Idle", "frame": {"x": 140, "y": 240, "w": 200, "h": 20}, "ts": now
        })
        t = 0
        while not self._stop.is_set():
            # For demo, toggle status text periodically
            label = "Idle" if (t % 8) < 4 else "Ready"
            self.store.upsert_node({
                "id": "txt:status", "role": "StaticText", "title": label, "frame": {"x": 140, "y": 240, "w": 200, "h": 20}, "ts": time.time()
            })
            t += 1
            time.sleep(period)

    def snapshot(self) -> Dict[str, Any]:
        return self.store.snapshot()

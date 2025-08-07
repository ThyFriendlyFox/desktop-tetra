from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class CRDTStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._doc: Dict[str, Any] = {"nodes": {}, "order": []}
        self._clock = 0

    def _tick(self) -> int:
        with self._lock:
            self._clock += 1
            return self._clock

    def upsert_node(self, node: Dict[str, Any]) -> str:
        with self._lock:
            node_id = node.get("id") or str(uuid.uuid4())
            node["ts"] = max(node.get("ts", 0), self._tick())
            self._doc["nodes"][node_id] = node
            if node_id not in self._doc["order"]:
                self._doc["order"].append(node_id)
            return node_id

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            if node_id in self._doc["nodes"]:
                del self._doc["nodes"][node_id]
            if node_id in self._doc["order"]:
                self._doc["order"].remove(node_id)

    def merge(self, other: Dict[str, Any]) -> None:
        with self._lock:
            for node_id, node in other.get("nodes", {}).items():
                cur = self._doc["nodes"].get(node_id)
                if cur is None or node.get("ts", 0) > cur.get("ts", 0):
                    self._doc["nodes"][node_id] = node
            for node_id in other.get("order", []):
                if node_id not in self._doc["order"]:
                    self._doc["order"].append(node_id)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            nodes = {k: dict(v) for k, v in self._doc["nodes"].items()}
            return {"nodes": nodes, "order": list(self._doc["order"]) }

    def query(self, role: Optional[str] = None, text_contains: Optional[str] = None) -> List[Dict[str, Any]]:
        snap = self.snapshot()
        out: List[Dict[str, Any]] = []
        for node_id in snap["order"]:
            n = snap["nodes"].get(node_id)
            if n is None:
                continue
            if role and n.get("role") != role:
                continue
            if text_contains and text_contains not in (n.get("title") or ""):
                continue
            out.append(n)
        return out

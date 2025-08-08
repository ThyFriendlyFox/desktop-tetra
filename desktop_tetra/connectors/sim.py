from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..interaction.sim.engine import SimEngine
from .base import DesktopConnector, Selector, SemanticNode


class SimConnector(DesktopConnector):
    def __init__(self) -> None:
        self.sim = SimEngine.instance()

    def build_semantic_map(self, app: Optional[str] = None, max_depth: int = 4) -> SemanticNode:
        return self.sim.snapshot()

    def find_element(self, selector: Selector, timeout_seconds: float = 3.0) -> Optional[Any]:
        snap = self.sim.snapshot()
        role = selector.get("role")
        title = selector.get("title")
        contains = bool(selector.get("contains", True))
        for node_id in snap.get("order", []):
            node = snap["nodes"][node_id]
            if role and node.get("role") != role:
                continue
            t = (node.get("title") or "")
            if title:
                if contains and title not in t:
                    continue
                if not contains and title != t:
                    continue
            return node
        return None

    def press(self, element: Any) -> bool:
        # Simple rule: pressing New sets status to Ready
        if isinstance(element, dict) and element.get("id") == "btn:new":
            self.sim.store.upsert_node({
                "id": "txt:status", "role": "StaticText", "title": "Ready", "frame": {"x": 140, "y": 240, "w": 200, "h": 20}
            })
            return True
        return True

    def set_value(self, element: Any, value: Any) -> bool:
        return True

    def focus_app(self, app: str) -> bool:
        return True

    def menu_select(self, path: List[str], app: Optional[str] = None, timeout_seconds: float = 3.0) -> bool:
        return True

    def scroll_to(self, selector: Selector, timeout_seconds: float = 3.0) -> bool:
        return True

    def wait_for(self, expect: Selector, state: Optional[Dict[str, Any]] = None, timeout_seconds: float = 3.0) -> bool:
        import time
        end = time.time() + timeout_seconds
        while time.time() < end:
            if self.find_element(expect, timeout_seconds=0.0) is not None:
                return True
            time.sleep(0.1)
        return False

    def get_element_bounds(self, element: Any) -> Tuple[float, float, float, float]:
        f = element.get("frame") if isinstance(element, dict) else None
        if not f:
            return (0.0, 0.0, 0.0, 0.0)
        return (float(f.get("x", 0)), float(f.get("y", 0)), float(f.get("w", 0)), float(f.get("h", 0)))

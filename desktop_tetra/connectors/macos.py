from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from ..ax import AXFinder
from .base import DesktopConnector, Selector, SemanticNode


class MacOSConnector(DesktopConnector):
    def __init__(self) -> None:
        self.ax = AXFinder()

    def build_semantic_map(self, app: Optional[str] = None, max_depth: int = 4) -> SemanticNode:
        return self.ax.build_semantic_map(app=app, max_depth=max_depth)

    def find_element(self, selector: Selector, timeout_seconds: float = 3.0) -> Optional[Any]:
        return self.ax.find_element(
            title=selector.get("title"),
            role=selector.get("role"),
            app=selector.get("app"),
            timeout_seconds=timeout_seconds,
            contains=bool(selector.get("contains", True)),
        )

    def press(self, element: Any) -> bool:
        return self.ax.press(element)

    def set_value(self, element: Any, value: Any) -> bool:
        return self.ax.set_value(element, value)

    def focus_app(self, app: str) -> bool:
        return self.ax.activate_app(app)

    def menu_select(self, path: List[str], app: Optional[str] = None, timeout_seconds: float = 3.0) -> bool:
        # Basic implementation via find by title/role for each level
        # Menu bar items are AXMenuBar -> AXMenu -> AXMenuItem
        end = time.time() + timeout_seconds
        current_el: Optional[Any] = None
        roles = ["AXMenuBarItem"] + ["AXMenuItem"] * (len(path) - 1)
        for idx, name in enumerate(path):
            remaining = max(0.2, end - time.time())
            el = self.ax.find_element(title=name, role=roles[idx], app=app, timeout_seconds=remaining, contains=False)
            if el is None:
                return False
            if not self.ax.press(el):
                return False
            current_el = el
            time.sleep(0.05)
        return current_el is not None

    def scroll_to(self, selector: Selector, timeout_seconds: float = 3.0) -> bool:
        # Try find and rely on AXScrollToVisible by pressing/focusing parent scroll area
        el = self.find_element(selector, timeout_seconds=timeout_seconds)
        if el is None:
            return False
        # Many controls support AXShowMenu/AXScrollToVisible; pressing often scrolls into view
        try:
            return self.ax.perform_action(el, "AXScrollToVisible") or True
        except Exception:
            return True

    def wait_for(self, expect: Selector, state: Optional[Dict[str, Any]] = None, timeout_seconds: float = 3.0) -> bool:
        end = time.time() + timeout_seconds
        while time.time() < end:
            el = self.find_element(expect, timeout_seconds=0.2)
            if el is not None:
                return True
            time.sleep(0.1)
        return False

    def get_element_bounds(self, element: Any) -> Tuple[float, float, float, float]:
        return self.ax.get_element_bounds(element)

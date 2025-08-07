from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from .base import DesktopConnector, Selector, SemanticNode


class WindowsConnector(DesktopConnector):
    def __init__(self) -> None:
        try:
            import uiautomation as uia  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("uiautomation package required on Windows. Install with `pip install uiautomation`.") from e
        self.uia = uia

    def build_semantic_map(self, app: Optional[str] = None, max_depth: int = 4) -> SemanticNode:
        uia = self.uia
        root = uia.GetRootControl()
        # Optionally filter by process if app provided
        def to_node(ctrl, depth: int) -> Dict[str, Any]:
            name = ctrl.Name
            automation_id = ctrl.AutomationId
            control_type = ctrl.ControlTypeName
            bounding = ctrl.BoundingRectangle
            node: Dict[str, Any] = {
                "role": control_type,
                "title": name,
                "identifier": automation_id,
                "frame": {"x": bounding.left, "y": bounding.top, "w": bounding.width(), "h": bounding.height()},
            }
            if depth <= 0:
                return node
            children = []
            try:
                for c in ctrl.GetChildren():
                    children.append(to_node(c, depth - 1))
            except Exception:
                pass
            if children:
                node["children"] = children
            return node
        return to_node(root, max_depth)

    def _find(self, selector: Selector, timeout_seconds: float) -> Optional[Any]:
        uia = self.uia
        conds = []
        title = selector.get("title")
        role = selector.get("role")
        identifier = selector.get("identifier")
        contains = bool(selector.get("contains", True))
        if title:
            conds.append(uia.NameContains(title) if contains else uia.NameEquals(title))
        if role:
            conds.append(uia.ControlTypeProperty == getattr(uia.ControlType, role, None))
        if identifier:
            conds.append(uia.AutomationIdProperty == identifier)
        cond = None
        for c in conds:
            cond = c if cond is None else cond & c
        start = time.time()
        while time.time() - start < timeout_seconds:
            try:
                ctrl = uia.Control(searchDepth=10, foundIndex=1, condition=cond)
                if ctrl and ctrl.Exists(0):
                    return ctrl
            except Exception:
                pass
            time.sleep(0.1)
        return None

    def find_element(self, selector: Selector, timeout_seconds: float = 3.0) -> Optional[Any]:
        return self._find(selector, timeout_seconds)

    def press(self, element: Any) -> bool:
        try:
            if element.InvokePattern().IsAvailable:
                element.InvokePattern().Invoke()
                return True
        except Exception:
            pass
        try:
            element.Click()  # uiautomation synthesizes via UIA, not raw cursor
            return True
        except Exception:
            return False

    def set_value(self, element: Any, value: Any) -> bool:
        try:
            if element.ValuePattern().IsAvailable:
                element.ValuePattern().SetValue(str(value))
                return True
        except Exception:
            pass
        return False

    def focus_app(self, app: str) -> bool:
        # app may be process name or window title
        uia = self.uia
        try:
            win = uia.WindowControl(searchDepth=2, Name=app)
            if win.Exists(0):
                win.SetFocus()
                return True
        except Exception:
            pass
        return False

    def menu_select(self, path: List[str], app: Optional[str] = None, timeout_seconds: float = 3.0) -> bool:
        # Traverse menubar → menu → item by Name
        uia = self.uia
        start = time.time()
        current = None
        for name in path:
            rem = max(0.2, timeout_seconds - (time.time() - start))
            sel = {"title": name, "role": "MenuItem", "contains": False}
            current = self._find(sel, rem)
            if current is None:
                return False
            if current.ExpandCollapsePattern().IsAvailable:
                try:
                    current.ExpandCollapsePattern().Expand()
                except Exception:
                    pass
            if current.InvokePattern().IsAvailable:
                try:
                    current.InvokePattern().Invoke()
                except Exception:
                    pass
            time.sleep(0.05)
        return current is not None

    def scroll_to(self, selector: Selector, timeout_seconds: float = 3.0) -> bool:
        ctrl = self._find(selector, timeout_seconds)
        if ctrl is None:
            return False
        try:
            if ctrl.ScrollItemPattern().IsAvailable:
                ctrl.ScrollItemPattern().ScrollIntoView()
                return True
        except Exception:
            pass
        return True

    def wait_for(self, expect: Selector, state: Optional[Dict[str, Any]] = None, timeout_seconds: float = 3.0) -> bool:
        start = time.time()
        while time.time() - start < timeout_seconds:
            if self._find(expect, 0.2) is not None:
                return True
            time.sleep(0.1)
        return False

    def get_element_bounds(self, element: Any) -> Tuple[float, float, float, float]:
        r = element.BoundingRectangle
        return (float(r.left), float(r.top), float(r.width()), float(r.height()))

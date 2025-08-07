from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from AppKit import NSWorkspace
from ApplicationServices import (
    AXIsProcessTrusted,
    AXUIElementCopyAttributeValue,
    AXUIElementCopyParameterizedAttributeValue,
    AXUIElementCopyActionNames,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    kAXChildrenAttribute,
    kAXFocusedWindowAttribute,
    kAXParentAttribute,
    kAXRoleAttribute,
    kAXTitleAttribute,
)

AXElement = Any


class AXFinder:
    def __init__(self) -> None:
        self.system_wide = AXUIElementCreateSystemWide()

    def is_accessibility_enabled(self) -> bool:
        return bool(AXIsProcessTrusted())

    def get_frontmost_app_bundle_id(self) -> Optional[str]:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        return app.bundleIdentifier()

    def _get_frontmost_app_ax(self) -> Optional[AXElement]:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        pid = app.processIdentifier()
        return AXUIElementCreateApplication(pid)

    def _get_app_by_bundle_or_name(self, bundle_or_name: str) -> Optional[AXElement]:
        ws = NSWorkspace.sharedWorkspace()
        for app in ws.runningApplications():
            if app.bundleIdentifier() == bundle_or_name or app.localizedName() == bundle_or_name:
                return AXUIElementCreateApplication(app.processIdentifier())
        return None

    def activate_app(self, bundle_or_name: str) -> bool:
        ws = NSWorkspace.sharedWorkspace()
        for app in ws.runningApplications():
            if app.bundleIdentifier() == bundle_or_name or app.localizedName() == bundle_or_name:
                return app.activateWithOptions(1)
        if ".app" in bundle_or_name or "/" in bundle_or_name:
            return bool(ws.launchApplication(bundle_or_name))
        return False

    def copy_attribute(self, element: AXElement, attribute: str) -> Any:
        try:
            err, value = AXUIElementCopyAttributeValue(element, attribute, None)
            if err:
                return None
            return value
        except Exception:
            return None

    def set_attribute(self, element: AXElement, attribute: str, value: Any) -> bool:
        try:
            err = AXUIElementSetAttributeValue(element, attribute, value)
            return not bool(err)
        except Exception:
            return False

    def copy_param_attribute(self, element: AXElement, attribute: str, param: Any) -> Any:
        try:
            err, value = AXUIElementCopyParameterizedAttributeValue(element, attribute, param, None)
            if err:
                return None
            return value
        except Exception:
            return None

    def get_actions(self, element: AXElement) -> List[str]:
        try:
            err, actions = AXUIElementCopyActionNames(element, None)
            if err or actions is None:
                return []
            return list(actions)
        except Exception:
            return []

    def perform_action(self, element: AXElement, action: str) -> bool:
        try:
            err = AXUIElementPerformAction(element, action)
            return not bool(err)
        except Exception:
            return False

    def _get_children(self, element: AXElement) -> List[AXElement]:
        value = self.copy_attribute(element, kAXChildrenAttribute)
        return list(value or [])

    def _get_title(self, element: AXElement) -> Optional[str]:
        title = self.copy_attribute(element, kAXTitleAttribute)
        return str(title) if title else None

    def _get_role(self, element: AXElement) -> Optional[str]:
        role = self.copy_attribute(element, kAXRoleAttribute)
        return str(role) if role else None

    def _get_parent(self, element: AXElement) -> Optional[AXElement]:
        return self.copy_attribute(element, kAXParentAttribute)

    def _frame_to_tuple(self, frame: Any) -> Tuple[float, float, float, float]:
        if frame is None:
            return (0.0, 0.0, 0.0, 0.0)
        if isinstance(frame, dict):
            return (
                float(frame.get("X", 0.0)),
                float(frame.get("Y", 0.0)),
                float(frame.get("Width", 0.0)),
                float(frame.get("Height", 0.0)),
            )
        if isinstance(frame, (tuple, list)) and len(frame) >= 4:
            return (float(frame[0]), float(frame[1]), float(frame[2]), float(frame[3]))
        try:
            origin = getattr(frame, "origin", None)
            size = getattr(frame, "size", None)
            if origin and size:
                return (float(origin.x), float(origin.y), float(size.width), float(size.height))
        except Exception:
            pass
        return (0.0, 0.0, 0.0, 0.0)

    def get_element_bounds(self, element: AXElement) -> Tuple[float, float, float, float]:
        frame = self.copy_attribute(element, "AXFrame")
        if frame is None:
            try:
                frame = self.copy_param_attribute(element, "AXFrameForRange", (0, 1))
            except Exception:
                frame = None
        if frame is None:
            win = self.copy_attribute(element, kAXFocusedWindowAttribute)
            frame = self.copy_attribute(win, "AXFrame") if win else None
        x, y, w, h = self._frame_to_tuple(frame)
        if w <= 0.0 and h <= 0.0:
            raise RuntimeError("Could not resolve element bounds")
        return x, y, w, h

    def _matches(self, element: AXElement, title: Optional[str], role: Optional[str], contains: bool) -> bool:
        if title is not None:
            actual = (self._get_title(element) or "").strip()
            expected = title.strip()
            if contains:
                if expected not in actual:
                    return False
            else:
                if actual != expected:
                    return False
        if role is not None:
            if (self._get_role(element) or "") != role:
                return False
        return True

    def find_element(self, title: Optional[str] = None, role: Optional[str] = None, app: Optional[str] = None, timeout_seconds: float = 0.0, contains: bool = False) -> Optional[AXElement]:
        end = time.time() + max(0.0, timeout_seconds)
        while True:
            root = self._get_app_by_bundle_or_name(app) if app else self._get_frontmost_app_ax()
            if root is not None:
                stack = [root]
                visited: set[int] = set()
                while stack:
                    current = stack.pop()
                    if id(current) in visited:
                        continue
                    visited.add(id(current))
                    try:
                        if self._matches(current, title, role, contains=contains):
                            return current
                        children = self._get_children(current)
                        stack.extend(children)
                    except Exception:
                        continue
            if time.time() >= end:
                break
            time.sleep(0.05)
        return None

    def build_semantic_map(self, app: Optional[str] = None, max_depth: int = 4) -> Dict[str, Any]:
        root = self._get_app_by_bundle_or_name(app) if app else self._get_frontmost_app_ax()
        if root is None:
            return {}

        def to_node(el: AXElement, depth: int) -> Dict[str, Any]:
            title = self._get_title(el)
            role = self._get_role(el)
            identifier = self.copy_attribute(el, "AXIdentifier")
            value = self.copy_attribute(el, "AXValue")
            enabled = self.copy_attribute(el, "AXEnabled")
            selected = self.copy_attribute(el, "AXSelected")
            actions = self.get_actions(el)
            try:
                x, y, w, h = self.get_element_bounds(el)
            except Exception:
                x = y = w = h = 0.0
            node: Dict[str, Any] = {
                "role": role,
                "title": title,
                "identifier": identifier,
                "value": value if isinstance(value, (str, int, float)) else None,
                "enabled": bool(enabled) if enabled is not None else None,
                "selected": bool(selected) if selected is not None else None,
                "actions": actions,
                "frame": {"x": x, "y": y, "w": w, "h": h},
            }
            if depth <= 0:
                return node
            children: List[AXElement] = []
            try:
                children = self._get_children(el)
            except Exception:
                children = []
            child_nodes: List[Dict[str, Any]] = []
            for c in children:
                try:
                    child_nodes.append(to_node(c, depth - 1))
                except Exception:
                    continue
            if child_nodes:
                node["children"] = child_nodes
            return node

        return to_node(root, max_depth)

    def press(self, element: AXElement) -> bool:
        return self.perform_action(element, "AXPress")

    def set_value(self, element: AXElement, value: Any) -> bool:
        return self.set_attribute(element, "AXValue", value)

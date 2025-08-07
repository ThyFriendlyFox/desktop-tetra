from __future__ import annotations

import time
from typing import Any, Dict, List

from Quartz.CoreGraphics import (
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventRightMouseDown,
    kCGEventRightMouseUp,
    kCGEventMouseMoved,
    kCGEventKeyDown,
    kCGEventKeyUp,
)

from .input_control import InputController


class ActionPlayer:
    def __init__(self, speed_multiplier: float = 1.0) -> None:
        self.speed = max(0.1, float(speed_multiplier))
        self.ctrl = InputController()

    def play(self, actions: List[Dict[str, Any]]) -> None:
        start = time.time()
        for act in actions:
            target_ts = act.get("ts", 0.0) / self.speed
            now = time.time()
            if target_ts > (now - start):
                time.sleep(max(0.0, target_ts - (now - start)))
            t = act.get("type")
            if t in (kCGEventLeftMouseDown, kCGEventLeftMouseUp):
                x, y = float(act.get("x", 0)), float(act.get("y", 0))
                self.ctrl.click_at_point(x, y, button="left")
            elif t in (kCGEventRightMouseDown, kCGEventRightMouseUp):
                x, y = float(act.get("x", 0)), float(act.get("y", 0))
                self.ctrl.click_at_point(x, y, button="right")
            elif t == kCGEventMouseMoved:
                x, y = float(act.get("x", 0)), float(act.get("y", 0))
                self.ctrl.move_mouse(x, y)
            elif t in (kCGEventKeyDown, kCGEventKeyUp):
                text = act.get("text", "")
                if text:
                    self.ctrl.type_text(text)

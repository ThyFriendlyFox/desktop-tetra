from __future__ import annotations

import time
from typing import Any, Dict, List

from Quartz.CoreGraphics import (
    CGEventTapCreate,
    CGEventTapEnable,
    kCGEventTapOptionListenOnly,
    CGEventGetLocation,
    CFMachPortCreateRunLoopSource,
    kCGHIDEventTap,
    kCGHeadInsertEventTap,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventRightMouseDown,
    kCGEventRightMouseUp,
    kCGEventMouseMoved,
    kCGEventKeyDown,
    kCGEventKeyUp,
)
from CoreFoundation import (
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRunInMode,
    CFRunLoopSourceInvalidate,
)


class ActionRecorder:
    def __init__(self, include_keys: bool = True, include_mouse: bool = True) -> None:
        self.include_keys = include_keys
        self.include_mouse = include_mouse
        self._events: List[Dict[str, Any]] = []
        self._start_ts = 0.0
        self._runloop_source = None
        self._tap = None

    def _handler(self, proxy, type_, event, refcon):
        if self._start_ts == 0.0:
            self._start_ts = time.time()
        now = time.time()
        t = int(type_)
        if self.include_mouse and t in (kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventRightMouseDown, kCGEventRightMouseUp, kCGEventMouseMoved):
            loc = CGEventGetLocation(event)
            self._events.append({
                "ts": now - self._start_ts,
                "type": t,
                "x": float(loc.x),
                "y": float(loc.y),
            })
        if self.include_keys and t in (kCGEventKeyDown, kCGEventKeyUp):
            self._events.append({
                "ts": now - self._start_ts,
                "type": t,
                "text": "",
            })
        return event

    def start(self) -> None:
        mask = 0
        if self.include_mouse:
            mask |= (1 << kCGEventLeftMouseDown) | (1 << kCGEventLeftMouseUp) | (1 << kCGEventRightMouseDown) | (1 << kCGEventRightMouseUp) | (1 << kCGEventMouseMoved)
        if self.include_keys:
            mask |= (1 << kCGEventKeyDown) | (1 << kCGEventKeyUp)
        self._tap = CGEventTapCreate(kCGHIDEventTap, kCGHeadInsertEventTap, kCGEventTapOptionListenOnly, mask, self._handler, None)
        if not self._tap:
            raise RuntimeError("Could not create event tap. Ensure Accessibility permissions are granted.")
        self._runloop_source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), self._runloop_source, "kCFRunLoopCommonModes")
        CGEventTapEnable(self._tap, True)

    def tick(self, seconds: float = 0.2) -> None:
        CFRunLoopRunInMode("kCFRunLoopDefaultMode", seconds, True)

    def stop(self) -> List[Dict[str, Any]]:
        if self._tap and self._runloop_source:
            CFRunLoopSourceInvalidate(self._runloop_source)
            self._tap = None
            self._runloop_source = None
        return list(self._events)

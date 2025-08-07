from __future__ import annotations

import time

from Quartz.CoreGraphics import (
    CGEventCreateKeyboardEvent,
    CGEventCreateMouseEvent,
    CGEventPost,
    CGEventSetFlags,
    CGEventSourceCreate,
    CGEventSourceSetLocalEventsSuppressionInterval,
    kCGEventSourceStateHIDSystemState,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGEventRightMouseDown,
    kCGEventRightMouseUp,
    kCGMouseButtonLeft,
    kCGMouseButtonRight,
    kCGHIDEventTap,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskControl,
)


KEYCODES = {
    "a": 0x00, "s": 0x01, "d": 0x02, "f": 0x03,
    "h": 0x04, "g": 0x05, "z": 0x06, "x": 0x07,
    "c": 0x08, "v": 0x09, "b": 0x0B, "q": 0x0C,
    "w": 0x0D, "e": 0x0E, "r": 0x0F, "y": 0x10,
    "t": 0x11, "1": 0x12, "2": 0x13, "3": 0x14,
    "4": 0x15, "6": 0x16, "5": 0x17, "=": 0x18,
    "9": 0x19, "7": 0x1A, "-": 0x1B, "8": 0x1C,
    "0": 0x1D, "]": 0x1E, "o": 0x1F, "u": 0x20,
    "[": 0x21, "i": 0x22, "p": 0x23, "l": 0x25,
    "j": 0x26, "'": 0x27, "k": 0x28, ";": 0x29,
    "\\": 0x2A, ",": 0x2B, "/": 0x2C, "n": 0x2D,
    "m": 0x2E, ".": 0x2F, "`": 0x32, " ": 0x31,
    "return": 0x24, "tab": 0x30, "delete": 0x33,
    "escape": 0x35,
}


class InputController:
    def __init__(self) -> None:
        source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
        self.source = source
        CGEventSourceSetLocalEventsSuppressionInterval(source, 0.0)

    def click_at_point(self, x: float, y: float, button: str = "left") -> None:
        btn = kCGMouseButtonLeft if button == "left" else kCGMouseButtonRight
        down_type = kCGEventLeftMouseDown if button == "left" else kCGEventRightMouseDown
        up_type = kCGEventLeftMouseUp if button == "left" else kCGEventRightMouseUp
        down = CGEventCreateMouseEvent(self.source, down_type, (x, y), btn)
        up = CGEventCreateMouseEvent(self.source, up_type, (x, y), btn)
        CGEventPost(kCGHIDEventTap, down)
        CGEventPost(kCGHIDEventTap, up)
        time.sleep(0.02)

    def move_mouse(self, x: float, y: float) -> None:
        evt = CGEventCreateMouseEvent(self.source, kCGEventMouseMoved, (x, y), kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, evt)

    def key_down_up(self, key: str, shift: bool = False, cmd: bool = False, alt: bool = False, control: bool = False) -> None:
        key_lower = key.lower()
        keycode = KEYCODES.get(key_lower)
        if keycode is None:
            return
        def post(down: bool) -> None:
            evt = CGEventCreateKeyboardEvent(self.source, keycode, down)
            flags = 0
            if shift:
                flags |= kCGEventFlagMaskShift
            if cmd:
                flags |= kCGEventFlagMaskCommand
            if alt:
                flags |= kCGEventFlagMaskAlternate
            if control:
                flags |= kCGEventFlagMaskControl
            if flags:
                CGEventSetFlags(evt, flags)
            CGEventPost(kCGHIDEventTap, evt)
        post(True)
        post(False)
        time.sleep(0.01)

    def type_text(self, text: str) -> None:
        for ch in text:
            if ch.isupper():
                self.key_down_up(ch.lower(), shift=True)
            else:
                self.key_down_up(ch)

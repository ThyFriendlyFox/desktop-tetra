from __future__ import annotations

import platform
from typing import Optional

from .base import DesktopConnector
from .macos import MacOSConnector


def get_connector(os_override: Optional[str] = None) -> DesktopConnector:
    name = (os_override or platform.system()).lower()
    if name == "darwin":
        return MacOSConnector()
    if name == "windows":
        from .windows import WindowsConnector
        return WindowsConnector()
    raise RuntimeError(f"Unsupported platform: {name}")

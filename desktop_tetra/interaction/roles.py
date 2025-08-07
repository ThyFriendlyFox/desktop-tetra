from __future__ import annotations

from typing import Optional


def normalize_role(os_role: Optional[str] = None, visual_role: Optional[str] = None) -> str:
    r = (os_role or visual_role or "").lower()
    mapping = {
        "axbutton": "Button",
        "axmenuitem": "MenuItem",
        "axmenubar": "MenuBar",
        "axtextfield": "TextField",
        "axstatictext": "StaticText",
        "region": "Region",
        "statictext": "StaticText",
        "menuitem": "MenuItem",
        "menu": "Menu",
        "menubar": "MenuBar",
        "edit": "TextField",
    }
    return mapping.get(r, os_role or visual_role or "Unknown")

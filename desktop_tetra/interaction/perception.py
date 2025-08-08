from __future__ import annotations

from typing import Any, Dict

from .engine import LiveEngine

try:
    from .sim.engine import SimEngine  # type: ignore
except Exception:  # pragma: no cover
    SimEngine = None  # type: ignore


def get_snapshot() -> Dict[str, Any]:
    if SimEngine is not None:
        eng = SimEngine.instance_if_running()
        if eng is not None:
            return eng.snapshot()
    return LiveEngine.instance().snapshot()

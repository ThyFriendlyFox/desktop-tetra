from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .connectors import get_connector
from .connectors.base import DesktopConnector
from .agent_core.wrapper_rules import OPERATING_PRINCIPLES, SYSTEM_PROMPT
from .llm import build_provider, LLMProvider
from .interaction.engine import LiveEngine
from .interaction.selector import score_candidates


class Agent:
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "openai", api_key: Optional[str] = None, base_url: Optional[str] = None, os_override: Optional[str] = None) -> None:
        self.model = model
        self.provider_name = provider
        self.provider: LLMProvider = build_provider(provider, model=model, api_key=api_key, base_url=base_url)
        self.conn: DesktopConnector = get_connector(os_override=os_override)

    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        messages = [
            {"role": "user", "content": OPERATING_PRINCIPLES},
            {"role": "user", "content": f"Goal: {goal}\nOptional context: {json.dumps(context or {}, ensure_ascii=False)}"},
        ]
        return self.provider.generate_json(system=SYSTEM_PROMPT, messages=messages)

    def _find(self, sel: Dict[str, Any], timeout: float = 3.0) -> Any:
        # Prefer live CRDT perception first; fall back to OS connector
        snap = LiveEngine.instance().snapshot()
        scored = score_candidates(snap, sel, top_k=3)
        if scored:
            # Return enriched selector node for downstream use; actions still executed via connector
            return {"node": scored[0][0], "selector": sel}
        return self.conn.find_element(sel, timeout_seconds=timeout)

    def _verify(self, expect: Dict[str, Any]) -> bool:
        return self.conn.wait_for(expect, timeout_seconds=1.5)

    def execute_steps(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        steps: List[Dict[str, Any]] = plan.get("steps", [])
        for step in steps:
            action = step.get("action")
            params = step.get("params", {})
            expect = step.get("expect", {})
            ok = False
            error: Optional[str] = None
            try:
                if action == "scan":
                    tree = self.conn.build_semantic_map(app=params.get("app"), max_depth=int(params.get("depth", 4)))
                    ok = True
                    results.append({"action": action, "ok": ok, "tree": tree})
                    continue
                if action == "focus_app":
                    ok = self.conn.focus_app(params["app"])  # type: ignore[index]
                elif action == "press":
                    el = self._find(params)
                    ok = bool(el and self.conn.press(el))
                elif action == "set_value":
                    el = self._find(params)
                    ok = bool(el and self.conn.set_value(el, params.get("value")))
                elif action == "menu_select":
                    ok = self.conn.menu_select(path=list(params.get("path", [])), app=params.get("app"))
                elif action == "scroll_to":
                    ok = self.conn.scroll_to(selector=params)
                elif action == "wait_for":
                    ok = self.conn.wait_for(expect=params, timeout_seconds=float(params.get("timeout", 3.0)))
                else:
                    error = f"Unknown action: {action}"
            except Exception as e:  # noqa: BLE001
                error = str(e)
            if ok and expect:
                ok = self._verify(expect)
            results.append({"action": action, "ok": ok, "error": error})
        return results

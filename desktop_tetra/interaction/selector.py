from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

from .roles import normalize_role


def score_candidates(snapshot: Dict[str, Any], selector: Dict[str, Any], top_k: int = 5) -> List[Tuple[Dict[str, Any], float, Dict[str, Any]]]:
    role = selector.get("role")
    title = selector.get("title")
    contains = bool(selector.get("contains", True))
    out: List[Tuple[Dict[str, Any], float, Dict[str, Any]]] = []
    for node_id in snapshot.get("order", []):
        node = snapshot["nodes"][node_id]
        nrole = normalize_role(visual_role=node.get("role"))
        score = 0.0
        reasons: Dict[str, Any] = {}
        if role and nrole == role:
            score += 2.0
            reasons["role"] = True
        title_text = (node.get("title") or "").strip()
        if title:
            if not contains and title_text == title:
                score += 4.0
                reasons["title_exact"] = True
            elif contains and title and title in title_text:
                score += 2.0
                reasons["title_contains"] = True
        # Prefer OCR nodes for text
        if node.get("source") == "ocr":
            score += 0.5
            reasons["ocr_bias"] = True
        if score > 0:
            out.append((node, score, reasons))
    out.sort(key=lambda t: t[1], reverse=True)
    return out[:top_k]

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import mss
import numpy as np
import pytesseract
from PIL import Image
import cv2

from .crdt import CRDTStore


class LiveFeed:
    def __init__(self, monitor_index: int = 1, target_fps: int = 4) -> None:
        self.monitor_index = monitor_index
        self.target_fps = max(1, target_fps)
        self._crdt = CRDTStore()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def crdt(self) -> CRDTStore:
        return self._crdt

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        with mss.mss() as sct:
            monitors = sct.monitors
            monitor = monitors[self.monitor_index if self.monitor_index < len(monitors) else 1]
            period = 1.0 / float(self.target_fps)
            while not self._stop.is_set():
                start = time.time()
                frame = sct.grab(monitor)
                img = Image.frombytes('RGB', frame.size, frame.rgb)
                self._process_frame(img)
                elapsed = time.time() - start
                sleep = max(0.0, period - elapsed)
                time.sleep(sleep)

    def _process_frame(self, pil_img: Image.Image) -> None:
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 120)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = gray.shape[:2]
        ocr = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        n = min(len(ocr.get("text", [])), len(ocr.get("conf", [])))
        now = time.time()
        for i in range(n):
            raw_txt = ocr["text"][i]
            txt = (raw_txt or "").strip()
            raw_conf = ocr["conf"][i]
            try:
                conf = int(raw_conf) if not isinstance(raw_conf, str) else int(raw_conf) if raw_conf.isdigit() else -1
            except Exception:
                conf = -1
            if not txt or conf < 50:
                continue
            x, y = int(ocr["left"][i]), int(ocr["top"][i])
            bw, bh = int(ocr["width"][i]), int(ocr["height"][i])
            node = {
                "id": f"ocr:{x}:{y}:{bw}:{bh}",
                "role": "StaticText",
                "title": txt,
                "frame": {"x": x, "y": y, "w": bw, "h": bh},
                "source": "ocr",
                "ts": now,
            }
            self._crdt.upsert_node(node)
        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < 40 or bh < 20:
                continue
            if x <= 0 or y <= 0 or x + bw >= w or y + bh >= h:
                continue
            node = {
                "id": f"region:{x}:{y}:{bw}:{bh}",
                "role": "Region",
                "title": None,
                "frame": {"x": int(x), "y": int(y), "w": int(bw), "h": int(bh)},
                "source": "cv",
                "ts": now,
            }
            self._crdt.upsert_node(node)

    def snapshot(self) -> Dict[str, Any]:
        return self._crdt.snapshot()

    def query(self, role: Optional[str] = None, text_contains: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._crdt.query(role=role, text_contains=text_contains)

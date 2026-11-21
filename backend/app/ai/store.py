"""Tiny JSON cache keyed by id + input hash. Committed to git so the demo never needs live calls."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

DATA_CACHE = Path(os.environ.get("DATA_CACHE_DIR", Path(__file__).resolve().parents[2] / "data_cache"))


class JsonStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.items: dict[str, dict] = {}
        try:
            self.items = json.loads(path.read_text()) if path.exists() else {}
        except (OSError, ValueError):
            self.items = {}

    def get(self, key: str, input_hash: str) -> dict | None:
        e = self.items.get(key)
        return e if e and e.get("input_hash") == input_hash else None

    def put(self, key: str, entry: dict) -> None:
        with self._lock:
            self.items[key] = entry

    def save(self) -> bool:
        """Atomic, best-effort (the deployed image may be read-only; entries then stay in memory)."""
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
                with os.fdopen(fd, "w") as fh:
                    json.dump(dict(sorted(self.items.items())), fh, ensure_ascii=False, indent=1)
                os.replace(tmp, self.path)
                return True
            except OSError:
                return False


def verdict_store() -> JsonStore:
    return JsonStore(Path(os.environ.get("VERDICTS_PATH", DATA_CACHE / "verdicts.json")))


def ward_summary_store() -> JsonStore:
    return JsonStore(Path(os.environ.get("WARD_SUMMARIES_PATH", DATA_CACHE / "ward_summaries.json")))


def trace_store() -> JsonStore:
    return JsonStore(Path(os.environ.get("TRACE_PATH", DATA_CACHE / "trace.json")))


def plan_store() -> JsonStore:
    return JsonStore(Path(os.environ.get("PLAN_EXPLANATIONS_PATH", DATA_CACHE / "plan_explanations.json")))

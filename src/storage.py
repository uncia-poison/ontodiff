"""
Simple JSON‑backed storage for self memory items.

The :class:`SelfMemoryStore` class reads and writes a JSON file on disk.  Each
entry in the memory is represented by the :class:`SelfMemoryItem` dataclass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any

@dataclass
class SelfMemoryItem:
    """Representation of a persisted self‑rule.

    Args:
        id: Unique identifier for the rule.
        about: The entity the rule describes.  Always ``"self"`` for self rules.
        kind: Category of rule (e.g. ``"style"``, ``"belief"``).
        claim: Human‑readable statement of the rule.
        key: Short machine‑friendly key identifying the rule.
        confidence: Estimated confidence in the rule.
        utility: Estimated usefulness of the rule.
        created_at: ISO‑8601 timestamp of first creation.
        last_seen_at: ISO‑8601 timestamp of the last time this rule was
            regenerated.
        recurrence: Count of how many times the rule has been seen.
        tags: Arbitrary list of strings describing signals which led to the rule.
    """

    id: str
    about: str
    kind: str
    claim: str
    key: str
    confidence: float
    utility: float
    created_at: str
    last_seen_at: str
    recurrence: int
    tags: List[str]


class SelfMemoryStore:
    """A simple on‑disk store for :class:`SelfMemoryItem` objects.

    By default the store writes to ``data/self_memory.json`` under the given
    ``root`` directory.  When persisting items the store deduplicates by
    ``key`` within the same ``about`` namespace.
    """

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)
        self.path: Path = self.root / "data" / "self_memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save({"items": []})

    def _load(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text() or "{\"items\": []}")

    def _save(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def upsert(self, item: SelfMemoryItem) -> None:
        data = self._load()
        items = data.get("items", [])
        for i, it in enumerate(items):
            if it.get("key") == item.key and it.get("about") == item.about:
                # Update existing entry
                it["last_seen_at"] = item.last_seen_at
                it["recurrence"] = it.get("recurrence", 1) + 1
                it["confidence"] = max(it.get("confidence", 0.0), item.confidence)
                it["utility"] = max(it.get("utility", 0.0), item.utility)
                items[i] = it
                data["items"] = items
                self._save(data)
                return
        # Otherwise append new
        items.append(asdict(item))
        data["items"] = items
        self._save(data)

    def list_items(self) -> List[SelfMemoryItem]:
        data = self._load()
        out: List[SelfMemoryItem] = []
        for it in data.get("items", []):
            out.append(SelfMemoryItem(**it))
        return out

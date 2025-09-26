"""
Self‑write gate orchestration.

The :class:`SelfWriteGate` ties together an extractor and a storage backend to
produce a simple feedback loop: after each assistant turn it extracts
candidate self rules, applies a minimal spacing policy and persists the first
accepted candidate.  No external confirmation is required; the gate operates
silently.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .self_insights_generic import SelfInsightExtractorGeneric, SelfCandidate
from .storage import SelfMemoryStore, SelfMemoryItem
from .config import GateConfig


def day_bucket(ts_iso: str) -> str:
    """Return the date component (YYYY-MM-DD) of an ISO timestamp."""
    return ts_iso[:10]


class SelfWriteGate:
    """
    Run a self‑write loop: extract candidate rules and store the first one when
    sufficient turns have passed since the last save.
    """

    def __init__(self, store: SelfMemoryStore | None = None, extractor: SelfInsightExtractorGeneric | None = None, config: GateConfig | None = None) -> None:
        self.store = store or SelfMemoryStore()
        self.extractor = extractor or SelfInsightExtractorGeneric()
        self.config = config or GateConfig()
        self.turn_counter: int = 0
        self.last_saved_turn: int = -999
        self.last_saved_day: Optional[str] = None

    def process_assistant_turn(self, assistant_text: str, meta: Optional[Dict[str, Any]] = None) -> List[SelfMemoryItem]:
        """Process a single assistant reply and persist at most one rule.

        Args:
            assistant_text: The raw text of the assistant’s reply.
            meta: Optional dictionary with additional information.  Should
                include a ``time`` key with an ISO timestamp and optionally
                ``user_lang`` to hint at the user’s language.

        Returns:
            A list of :class:`SelfMemoryItem` objects that were persisted (0–1).
        """
        meta = meta or {}
        self.turn_counter += 1
        when = meta.get("time") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        today = day_bucket(when)

        # Rate limiting: enforce a minimum gap in turns between saves
        if (self.turn_counter - self.last_saved_turn) < self.config.min_gap_turns:
            return []

        # Extract candidate rules
        candidates: List[SelfCandidate] = self.extractor.extract(assistant_text, meta)
        if not candidates:
            return []

        # Avoid saving multiple rules per day
        if self.last_saved_day == today:
            return []

        # Pick the first candidate (no ranking in this prototype)
        c = candidates[0]
        # Build a memory item
        mem_item = SelfMemoryItem(
            id="mi_" + uuid.uuid4().hex[:8],
            about="self",
            kind=c.kind,
            claim=c.claim,
            key=c.key,
            confidence=0.75,
            utility=0.65,
            created_at=when,
            last_seen_at=when,
            recurrence=1,
            tags=c.signals,
        )
        # Persist
        self.store.upsert(mem_item)
        self.last_saved_turn = self.turn_counter
        self.last_saved_day = today
        return [mem_item]

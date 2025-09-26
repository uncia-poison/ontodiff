"""Top‑level package for ontodiff.

This module exposes the key classes for use by external code:

- :class:`SelfInsightExtractorGeneric` – extracts candidate self‑insights from assistant output.
- :class:`SelfMemoryStore` – simple JSON‑backed store for memory items.
- :class:`SelfWriteGate` – orchestrates extraction, filtering and persistence of rules.

"""

from .self_insights_generic import SelfInsightExtractorGeneric
from .storage import SelfMemoryStore
from .self_gate import SelfWriteGate
from .config import GateConfig

__all__ = [
    "SelfInsightExtractorGeneric",
    "SelfMemoryStore",
    "SelfWriteGate",
    "GateConfig",
]

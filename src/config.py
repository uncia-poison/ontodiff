"""
Configuration classes for the ontodiff self‑write‑gate.

The :class:`GateConfig` dataclass defines a few tunable parameters for the write
gate.  In this simplified implementation most values are unused, but they are
provided to illustrate where more advanced logic could be injected.
"""

from dataclasses import dataclass


@dataclass
class GateConfig:
    """Configuration for the self‑write‑gate.

    Attributes:
        accept_threshold: Score above which a candidate insight is accepted.
        min_gap_turns: Minimum number of assistant turns between two saves.
        long_len_threshold: Threshold of characters beyond which a reply is
            considered too long.
    """

    accept_threshold: float = 0.7
    min_gap_turns: int = 6
    long_len_threshold: int = 1200

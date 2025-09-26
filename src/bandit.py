"""
Simple multi‑armed bandit for rule selection.

In this prototype we use a uniform random choice among available rules.  A more
advanced implementation might use Thompson sampling or another contextual
bandit algorithm.  The class is used by the write gate to decide which of
several competing self rules to apply in a given context.
"""

import random


class SimpleBandit:
    """A trivial bandit that picks a random arm and tracks successes and failures."""

    def __init__(self) -> None:
        self.success: dict[str, int] = {}
        self.failure: dict[str, int] = {}

    def add_if_absent(self, arm: str) -> None:
        """Register a new arm if it does not already exist."""
        if arm not in self.success:
            self.success[arm] = 1
            self.failure[arm] = 1

    def select(self) -> str | None:
        """Select an arm uniformly at random.

        Returns:
            The name of the selected arm, or ``None`` if no arms exist.
        """
        arms = list(self.success.keys())
        return random.choice(arms) if arms else None

    def update(self, arm: str, reward: float) -> None:
        """Update the bandit with the result of choosing an arm.

        Args:
            arm: The arm that was selected.
            reward: Positive values indicate a success, non‑positive a failure.
        """
        if arm not in self.success:
            self.add_if_absent(arm)
        if reward > 0:
            self.success[arm] += 1
        else:
            self.failure[arm] += 1

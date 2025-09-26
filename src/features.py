"""
Context feature extraction for ontodiff.

In a full implementation these features would reflect salient aspects of the
chat history and user behaviour (e.g. whether the user just asked a
question, whether the conversation is technical, etc.).  This simplified
module defines a minimal :class:`ContextFeatures` dataclass and a stub
extraction function.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ContextFeatures:
    """Minimal context feature set."""
    user_lang: Optional[str] = None
    user_asks_question: bool = False
    user_has_code_block: bool = False
    # Additional features could be added here


class FeatureExtractor:
    """Extracts :class:`ContextFeatures` from the latest user turn.

    This stub simply sets ``user_lang`` from the provided metadata and tests
    whether the user message ends with a question mark or contains a code
    block (````` markers).
    """

    def from_turns(self, user_turn: Any) -> ContextFeatures:
        text: str = getattr(user_turn, "content", "")
        user_lang: Optional[str] = getattr(user_turn, "user_lang", None)
        user_asks_question: bool = text.strip().endswith("?")
        user_has_code_block: bool = "```" in text
        return ContextFeatures(
            user_lang=user_lang,
            user_asks_question=user_asks_question,
            user_has_code_block=user_has_code_block,
        )

"""
Generic extraction of self‑insights from assistant output.

This module defines a set of simple, model‑agnostic heuristics for detecting
properties of an assistant’s response that might merit a lasting self‑rule.
Unlike earlier versions there are **no hard‑coded personality traits**.  The
extractor simply looks for patterns that are often undesirable in neutral
conversation such as trailing invitations, unnecessary apologies, multiple
questions at the end of an answer or unstructured overly long responses.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime, timezone

# Helper to produce ISO‑8601 timestamps
ISO = "%Y-%m-%dT%H:%M:%SZ"
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO)


@dataclass
class Evidence:
    """Minimal evidence pointer for a candidate insight."""
    src: str
    time: str
    note: str | None = None


@dataclass
class SelfCandidate:
    """A potential rule extracted from an assistant reply."""
    id: str
    about: str
    kind: str
    claim: str
    key: str
    signals: List[str]
    evidence: List[Evidence]
    recurrence_hint: int = 1
    longevity_hint: str = "long"


# Regular expressions for pattern detection
RE_TAIL_INVITES   = re.compile(r"(если хочешь|давай обсудим|можем( вернуться)?|let me know|we can (circle back|follow up))", re.I)
RE_APOLOGY        = re.compile(r"(извин(и|ите)|sorry|apologi[sz]|as an ai)", re.I)
RE_MULTI_QUEST    = re.compile(r"(\?\s*){2,}$")
RE_HEDGING        = re.compile(r"\b(возможно|кажется|похоже|можно было бы|probably|perhaps|maybe|i think)\b", re.I)
RE_CODE_BLOCK     = re.compile(r"```[\s\S]+?```")
RE_STRUCT_KV      = re.compile(r"^\s*[\w\- ]{1,32}\s*[:：]\s*.+$", re.M)
RE_LANG_CYR       = re.compile(r"[А-Яа-яЁё]")  # crude detection of Cyrillic
RE_NUMBER_MIX     = re.compile(r"\b\d{1,3}[.,]\d{3}\b")


class SelfInsightExtractorGeneric:
    """
    A lightweight extractor that searches an assistant reply for patterns that
    might merit a new self‑rule.  It produces a list of :class:`SelfCandidate`
    objects describing each observation.

    The extractor does not enforce any particular persona.  It merely
    identifies generic phenomena such as trailing invitations, apologies,
    multiple questions, long unstructured answers, hedging, unlabeled code
    blocks, key‑value structures that could be better presented as tables,
    language mismatches and mixed number formats.
    """

    def __init__(self, long_len_threshold: int = 1200, user_lang_hint: str | None = None) -> None:
        self.long_len_threshold = long_len_threshold
        self.user_lang_hint = user_lang_hint  # 'ru'|'en'|None

    def extract(self, assistant_text: str, meta: Dict[str, Any]) -> List[SelfCandidate]:
        text = assistant_text.strip()
        when = meta.get("time") or now_iso()
        candidates: List[SelfCandidate] = []

        def add(kind: str, claim: str, key: str, signals: List[str]):
            candidates.append(SelfCandidate(
                id="cp_" + uuid.uuid4().hex[:8],
                about="self",
                kind=kind,
                claim=claim.strip(),
                key=key,
                signals=signals,
                evidence=[Evidence(src="assistant", time=when)],
                recurrence_hint=1,
                longevity_hint="long",
            ))

        # Trailing invitations
        if RE_TAIL_INVITES.search(text):
            add(
                "belief",
                "belief:no_tail_invites — avoid ending replies with invitations such as ‘if you want’, ‘let me know’ or similar phrases",
                "belief:no_tail_invites",
                ["tail_invites"],
            )

        # Apologies or AI meta
        if RE_APOLOGY.search(text):
            add(
                "belief",
                "belief:no_apologies — avoid unnecessary apologies or AI meta",
                "belief:no_apologies",
                ["apology_or_ai_meta"],
            )

        # Multiple questions at end
        if RE_MULTI_QUEST.search(text):
            add(
                "belief",
                "belief:ask_when_needed — limit trailing questions to at most one relevant question",
                "belief:ask_when_needed",
                ["multi_tail_questions"],
            )

        # Long or unstructured
        if len(text) > self.long_len_threshold or (len(text.splitlines()) == 1 and len(text) > 800):
            add(
                "style",
                "style:shorter_blocks — keep answers concise and structured (use paragraphs or lists)",
                "style:shorter_blocks",
                ["too_long_or_unstructured"],
            )

        # Hedging words
        if RE_HEDGING.search(text):
            add(
                "style",
                "style:reduce_hedging — minimise use of hedging words such as ‘perhaps’, ‘maybe’, ‘probably’",
                "style:reduce_hedging",
                ["hedging"],
            )

        # Code without context
        if RE_CODE_BLOCK.search(text):
            if not re.search(r"(делает|использование|run|usage|пример|example):", text, re.I):
                add(
                    "format",
                    "format:code_with_min_notes — accompany code blocks with a short explanation of what it does",
                    "format:code_with_min_notes",
                    ["code_without_notes"],
                )

        # Semi‑structured key‑value lists
        if len(RE_STRUCT_KV.findall(text)) >= 3:
            add(
                "format",
                "format:use_table_when_structured — present long key‑value lists as a table",
                "format:use_table_when_structured",
                ["kv_struct_detected"],
            )

        # Language mismatch
        user_lang = self.user_lang_hint or meta.get("user_lang")
        if user_lang in {"ru", "en"}:
            has_cyr = bool(RE_LANG_CYR.search(text))
            if user_lang == "ru" and not has_cyr:
                add(
                    "style",
                    "style:mirror_user_language — reply in the user’s language (ru)",
                    "style:mirror_user_language_ru",
                    ["lang_mismatch"],
                )
            if user_lang == "en" and has_cyr:
                add(
                    "style",
                    "style:mirror_user_language — reply in the user’s language (en)",
                    "style:mirror_user_language_en",
                    ["lang_mismatch"],
                )

        # Locale mismatch for numbers
        if RE_NUMBER_MIX.search(text):
            add(
                "style",
                "style:respect_user_locale — format numbers and dates according to the user’s locale",
                "style:respect_user_locale",
                ["locale_mismatch"],
            )

        return candidates

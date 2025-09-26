"""
Command line interface for ontodiff.

Usage:
    python -m ontodiff.cli <jsonl_file> [--root <output_dir>]

This will read a JSON Lines file containing a chat transcript.  Each line must
be a JSON object with at least ``role`` ("user" or "assistant") and
``content`` fields.  Optional ``time`` and ``user_lang`` fields will be used

to set metadata for the self‑write‑gate.  Only assistant replies are
processed; user messages are ignored by the write gate.  Persisted rules are
written to ``data/self_memory.json`` under the root directory.
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path

from .self_gate import SelfWriteGate
from .storage import SelfMemoryStore
from .self_insights_generic import SelfInsightExtractorGeneric


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the ontodiff self‑write‑gate on a chat log.")
    parser.add_argument("jsonl", help="Path to a JSON Lines chat log")
    parser.add_argument("--root", default=".", help="Output directory for memory files")
    args = parser.parse_args()

    path = Path(args.jsonl)
    if not path.exists():
        raise SystemExit(f"Input file {args.jsonl} does not exist")

    store = SelfMemoryStore(root=args.root)
    extractor = SelfInsightExtractorGeneric()
    gate = SelfWriteGate(store=store, extractor=extractor)

    # Process the chat line by line
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Only process assistant turns
            if msg.get("role") != "assistant":
                continue
            text = msg.get("content", "")
            meta = {
                "time": msg.get("time"),
                "user_lang": msg.get("user_lang"),
            }
            gate.process_assistant_turn(text, meta)

    # Print summary of stored rules
    items = store.list_items()
    for it in items:
        print(f"{it.key}: {it.claim}")


if __name__ == "__main__":
    main()

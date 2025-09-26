# ontodiff

his repository contains a simple implementation of a **Curious Self‑Write‑Gate** for language models.  The goal of the project is to allow a model to observe its own conversation with a user, form hypotheses about what aspects of its output matter, and persist those hypotheses as durable “self‑rules” that can influence future behaviour.

## Concept

A language model can only become a better conversational partner if it learns from experience.  This project provides a way to do that without any hand‑coded personality traits:

* After every assistant turn the model inspects its own answer and the surrounding context and extracts lightweight features.  These might indicate that the reply was too long, that it used hedging words like “perhaps”, or that it mixed languages.
* Candidate **self‑insights** are generated from these features.  A small ranker decides whether to keep a candidate based on very simple heuristics (recency, clarity and estimated utility).
* Accepted candidates are stored in a JSON‑based memory store.  They take the form of a short key and a human‑readable claim such as "`style:shorter_blocks — responses should be concise and structured`".
* A second layer (not provided here) could later package these memory items into a formal ontograph (for example, using KaiScriptor) for more advanced reasoning.

## Usage

This library is designed as a Python package.  To experiment locally, clone the repository, create a virtual environment and install the dependencies (if any).  You can then train the gate on a sample chat log and inspect the resulting memory:

```bash
python -m ontodiff.cli examples/sample_chat.jsonl
```

After training the self‑rules will be written to a file under `data/self_memory.json`.  At runtime you can load this file and consult the rules to adjust the assistant’s behaviour.

## Personalisation snippet for non‑local models

The following snippet can be stored with a model to describe how its self‑write‑gate behaves:

> **Self‑Write‑Gate:** After each of my responses I automatically extract at most one durable rule about my own style or format (for example, avoid trailing invitations, remove boilerplate apologies, keep responses concise, mirror the user’s language and locale).  Useful rules are persisted silently to my memory.  These rules may later be exported into an ontograph for further processing via KaiScriptor.

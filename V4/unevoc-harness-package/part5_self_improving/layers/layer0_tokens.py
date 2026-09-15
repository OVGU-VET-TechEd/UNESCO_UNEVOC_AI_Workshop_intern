#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layer0_tokens.py — Layer 0: how many tokens does YOUR model really see?

    python layer0_tokens.py
    python layer0_tokens.py --model qwen3-vl:8b --text "Your own sentence"

The page uses a rough JavaScript splitter. This asks the local model instead:
Ollama reports `prompt_eval_count`, the number of tokens the model's own
tokenizer produced for the prompt. `raw` mode sends the text without a chat
template, so the count is the text alone.
"""

from __future__ import annotations

import re

import layer_common as lc

# The page's example sentence, plus the same sentence in other languages, to show
# that token cost is not neutral across languages.
SAMPLES = [
    ("English", "Write one learning objective for hydraulic system safety."),
    ("German", "Formuliere ein Lernziel zur Sicherheit von Hydrauliksystemen."),
    ("French", "Rédigez un objectif d'apprentissage sur la sécurité des systèmes hydrauliques."),
    ("Spanish", "Escribe un objetivo de aprendizaje sobre la seguridad de los sistemas hidráulicos."),
]


def page_estimate(text: str) -> int:
    """The same rough splitter the HTML page uses, for comparison."""
    count = 0
    for piece in re.findall(r"[A-Za-z]+|[0-9]+|[^\sA-Za-z0-9]", text):
        count += -(-len(piece) // 4) if piece.isalpha() and len(piece) > 6 else 1
    return count


def real_tokens(model: str, text: str) -> int:
    # Some tokenizers add one begin-of-text token; that is part of what the model sees.
    reply = lc.generate(model, text, raw=True, num_predict=1)
    return int(reply.get("prompt_eval_count", 0))


def main() -> int:
    args = lc.parse_args(__doc__.splitlines()[1],
                         lambda p: p.add_argument("--text", action="append",
                                                  help="extra text to measure (repeatable)"))
    lc.require_model(args.model)
    samples = SAMPLES + [("your text", t) for t in (args.text or [])]

    rows = ["| Language | Words | Page estimate | Real tokens | Tokens per word |",
            "|---|---:|---:|---:|---:|"]
    results = []
    print(f"Model: {args.model}\n")
    print(f"{'language':10} {'words':>5} {'page est.':>9} {'real':>5} {'tok/word':>8}")
    for label, text in samples:
        words = len(text.split())
        real = real_tokens(args.model, text)
        estimate = page_estimate(text)
        ratio = real / words if words else 0
        print(f"{label:10} {words:5} {estimate:9} {real:5} {ratio:8.2f}   {text}")
        rows.append(f"| {label}: {text} | {words} | {estimate} | {real} | {ratio:.2f} |")
        results.append({"language": label, "text": text, "words": words,
                        "page_estimate": estimate, "real_tokens": real,
                        "tokens_per_word": round(ratio, 2)})

    body = ("Token counts reported by the model's own tokenizer (`prompt_eval_count`, "
            "raw mode, no chat template). The page estimate is the HTML page's rough "
            "splitter.\n\n" + "\n".join(rows) +
            "\n\nIf a count looks too small, Ollama may have reused a cached prompt prefix; "
            "run again after `ollama stop " + args.model + "`.")
    lc.write_report("layer0_tokens.md", "Layer 0 — tokens", args.model, body)
    lc.write_data("layer0_tokens", args.model, {"samples": results})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

---
applyTo: "**/*.py"
description: Coding rules for this package. The code is teaching material that happens to run.
---

# Python rules

Readers include TVET instructors and researchers who do not write software. Code in this
repository is read more often than it is run.

## Structure

- **Standard library only** for anything in the harness: state, verification, logging, the
  Ollama client, retrieval, chunking, citation checking. If you reach for a dependency here,
  stop — the point is that these parts are inspectable without installing anything.
- Third-party packages are permitted only for document work: `pdfplumber`, `matplotlib`,
  `reportlab`. Do not add others without a `feature_list.json` item.
- Keep the numbered section banners (`# === 1. RETRIEVE ===`). They are how a non-programmer
  navigates the file. Add to them; do not remove them.

## Comments

- Every non-obvious block gets a comment explaining **why**, not what.
- Every module opens with a docstring that says what it does, how to run it, and — where
  relevant — which parts are harness and which part is the model call. That distinction is the
  single most important teaching point in the package.
- Never delete a comment that explains a limitation. Those are load-bearing.

## Network

The only permitted host is `127.0.0.1:11434`, read from `OLLAMA_URL` with that default. Any other
URL in a non-comment line fails `make verify`.

## Verification and loops

- Every retry loop has a **named constant** bounding it. No `while True`.
- Every verification function is deterministic and model-free. A check performed by a model is
  not a check.
- Errors are reported with the reason, in a sentence, and written to the log file — not swallowed.

## Style

- Descriptive names over short ones: `passages`, not `ps`. Loop variables may be short.
- Type hints on function signatures.
- No f-string in a `log()` call that could raise if a value is `None`.
- Line length 96.

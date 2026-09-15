---
name: Verification and done-ness
alwaysApply: true
---

# `make verify` is the definition of done

Never report work as complete without running it and pasting the output. Your own assessment that
the code looks right does not count — that is the exact failure mode this package teaches about.

```
make verify    syntax · JSON · structure · offline-only · LiaScript · anonymisation leaks
               · knowledge base integrity · Markdown links
make demo      end-to-end smoke test of Parts 2-4 against the mock server, no model needed
make eval      the assistant against the fixed question set, three separate rates
```

## Rules

- An item is `passing` only when `make verify` exits 0 **and** its output is pasted into the
  `evidence` field of `feature_list.json`.
- If the demo assistant changed, `make eval` must also run, and **all three rates** recorded.
  A change that improves phrasing while lowering the refusal rate is a regression.
- Every retry loop needs a named constant bounding it. No `while True`.
- Every verification function is deterministic and model-free. A check performed by a model is
  not a check.
- **Generator ≠ evaluator.** When acting as `@qa`, do not fix what you find. Describe the fix and
  say which role owns it.

## What these checks cannot do

They check shapes, syntax, structure and integrity. They cannot tell you whether the teaching
content is sound, whether a citation supports its claim, whether a document contains indirect
identifiers, or whether an answer was correct. State this limitation whenever you report a pass.

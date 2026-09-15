---
name: eval-assistant
description: Evaluate the demo assistant and diagnose which of the three rates is the problem.
agent: Librarian
argument-hint: model tag, e.g. llama3.1:8b
tools: ['edit', 'runCommands']
---

Run `make eval MODEL=${input:model:llama3.1:8b}`.

Report **all three rates separately**. A blended accuracy figure is not acceptable output.

| Rate | If it is low |
|---|---|
| Retrieval hit | corpus, chunking or metadata. **Do not touch thresholds or the model.** Hand off to Curator. |
| Answered when expected | thresholds too strict, or the corpus lacks the material |
| Refused when expected | thresholds too loose — the serious one |

If tuning is warranted:

- change **one** constant at the top of `ask.py`, not two;
- re-run and report before and after;
- state explicitly whether the refusal rate moved. A change that improves phrasing while lowering
  the refusal rate is a regression, and you must call it one.

If the model tag is `mock:demo`, say clearly that the output is canned and reflects control flow
only, not answer quality.

Finish by recording the rates in `PROGRESS.md`.

---
name: refresh-corpus
description: Run workflow W1 — corpus refresh, with the mandatory human checkpoint.
agent: Curator
argument-hint: what changed in corpus_raw/
tools: ['edit', 'runCommands', 'vscode/askQuestions']
---

Run workflow [W1 — Corpus refresh](../../bmad/workflows/W1_corpus_refresh.md).

Changes described by the user: ${input:changes:what was added, changed or removed}

Steps:

1. Confirm what is now in `part4_unesco_brief/demo_assistant/corpus_raw/`. List every document.
2. Run `make corpus`.
3. **STOP.** Open `anonymisation_report.md`. Summarise, per document, what was removed and what
   was reported as clean. Then use #tool:vscode/askQuestions to ask the human to confirm before
   indexing. Do not proceed on an assumption.
4. After explicit confirmation only: `make kb`.
5. `make verify` and paste the output.
6. Remind the user that `make eval` should follow, because a corpus change usually moves the
   retrieval hit rate.

Flag loudly if any document is a PDF — `anonymise.py` copies PDFs through unscrubbed.

Do not claim the corpus is anonymised. Report what was removed.

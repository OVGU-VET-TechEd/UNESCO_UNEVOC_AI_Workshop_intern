# W1 — Corpus refresh

**Use when:** documents have been added, changed or withdrawn.
**Chain:** `@curator` → *human* → `@curator` → `@librarian` → `@qa`

| # | Who | Step | Exit condition |
|---|---|---|---|
| 1 | `@curator` | Update `corpus_raw/`. Name every document added or removed. | The folder reflects the intended corpus |
| 2 | `@curator` | `make corpus` | `anonymisation_report.md` regenerated |
| 3 | **human** | Read the report end to end. Look for indirect identifiers the tool cannot see. | Explicit confirmation, or documents returned to step 1 |
| 4 | `@curator` | `make kb` | `kb.json` rebuilt; `make verify` knowledgebase check passes |
| 5 | `@librarian` | `make eval` | Three rates recorded, before and after |
| 6 | `@qa` | `make verify` + report | Exit 0, limitations stated |

**Do not skip step 3.** It is the only step in this workflow that a machine cannot perform, and
it is the one that matters. If the corpus changed and nobody read the report, the corpus is not
cleared regardless of what the checks say.

**Expected side effect:** changing the corpus usually moves the retrieval hit rate. If it moves
down, the cause is step 1 or 2, not the model.

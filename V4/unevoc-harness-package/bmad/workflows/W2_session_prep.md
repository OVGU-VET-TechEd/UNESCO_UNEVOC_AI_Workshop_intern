# W2 — Session preparation

**Use when:** a UNEVOC session is scheduled. Run this the day before, not the morning of.
**Chain:** `@qa` → `@librarian` → *human* → `@packager` (optional)

| # | Who | Step | Exit condition |
|---|---|---|---|
| 1 | `@qa` | `make verify` and `make demo` on the machine that will be used in the room | Both exit 0 on **that** machine |
| 2 | `@librarian` | `make eval MODEL=<the model actually installed>` — not the mock | Three rates recorded against the real model |
| 3 | `@librarian` | Run the two demonstration questions live: one covered, one not covered | The covered one answers with citations; the uncovered one refuses |
| 4 | **human** | Walk `part2_teaching/RUNBOOK_*.md` from step 0 on the room's machine | Every ✅ check passes |
| 5 | **human** | Complete `bmad/checklists/session_readiness.md` | Every box ticked or a stated fallback |
| 6 | `@packager` | Only if handing the package to attendees: `make package` | Archive verifies from a fresh extraction |

**The single most common failure** is a model that was never pulled on the room's machine. Step 1
catches it a day early. `make demo` uses the mock server and needs no model, so it does **not**
catch it — step 2 is what catches it, which is why step 2 forbids the mock.

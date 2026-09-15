---
name: session-prep
description: Run workflow W2 — prepare this machine for a UNEVOC session tomorrow.
agent: UNEVOC Lead
argument-hint: the model tag installed on this machine
---

Run workflow [W2 — Session preparation](../../bmad/workflows/W2_session_prep.md) on **this**
machine.

1. `make verify` and `make demo`. Both must exit 0 here, not on someone else's laptop.
2. `ollama list`. Confirm the models the runbook assumes are actually present.
3. `make eval MODEL=${input:model:llama3.1:8b}` — **not** the mock. `make demo` uses the mock and
   so cannot catch a missing model; this step is what catches it.
4. Run the two demonstration questions live:
   - a covered one — must answer with citations
   - "What is the capital city of Peru?" — must refuse, and the log should show the refusal
     happened at the retrieval gate, before any model call
5. Walk `bmad/checklists/session_readiness.md` and report every unticked box with a fallback.

If a model check fails and cannot be fixed, say clearly that the session must run on the mock
server and that this must be stated repeatedly to the room. Canned output presented as model
output would undo the point of the session.

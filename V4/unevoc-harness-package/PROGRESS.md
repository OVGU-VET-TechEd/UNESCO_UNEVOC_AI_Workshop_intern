# PROGRESS.md

Read this first, every session. It is the truth about where things stand — not the chat history.
Append new records; never rewrite old ones.

## Current verified state

- Repository root:          this folder
- One-time setup:           `make init`
- Standard verify command:  `make verify`  (exits 0 today)
- Smoke test:               `make demo`    (uses the mock server; needs no model)
- Highest-priority unfinished item: `real-model-validation`
- Current blocker:          none, but see the risk below

## Standing risks

1. **Everything runnable has been verified against `tools/mock_ollama.py` only.** The mock
   returns canned text. It exercises control flow — retrieval gate, citation check, retry,
   stop condition, harness overrides — and nothing else. No component in this package has been
   validated against a real local model. That is item `real-model-validation`, and it is
   blocking for any session.
2. **Retrieval thresholds are corpus-specific.** `MIN_RETRIEVAL_SCORE=5.0` and
   `MIN_TERM_COVERAGE=0.55` separate the demo corpus's answerable questions (coverage 0.57–1.00)
   from its unanswerable ones (0.00–0.50). That is a narrow margin. Any new corpus needs
   re-tuning via `make eval`.
3. **Dated claims.** The package states that no post-2024 revision of the UNESCO frameworks was
   found as of July 2026. Re-check before any external use (workflow W3 step 2).

## Session records

### 2026-07-29 — interactive learning page + layer 5

- **Goal:** an interactive HTML page teaching the progression from a single prompt to
  self-improving agents, and a runnable implementation of that last layer.
- **Completed:**
  - `part5_self_improving/LEARN_the_five_layers.html` — six layers (0 foundations, 1 prompting,
    2 skills, 3 harness, 4 loop, 5 self-improvement), a persistent prompt inspector that grows as
    you advance, three replay demos, and per-layer UNESCO mappings. Self-contained, no network.
  - `part5_self_improving/wiki_agent.py` — a scaled-down WikiSkill loop (raw/ wiki/ skills/,
    four roles, validation gating with rollback) against local Ollama.
  - `tools/mock_ollama.py` extended so the evolution loop runs with no model, with a gradient and
    one deliberate regression so a rollback is visible.
  - `make evolve` and `make learn` targets; `make demo` now covers Part 5.
  - `tools/verify_package.py` offline check extended to HTML: remote assets and browser storage
    now fail the build.
- **Verification run:** `make verify` → exit 0. `make demo` → exit 0, layer-5 arc
  0% → 33% → 67% → ROLLED BACK → 100%.
- **Evidence:** recorded in `feature_list.json` under `interactive-learning-page`.
- **Known risks:** the page's demos are replays, clearly labelled as such in the page footer and
  in the Part 5 README. Still no real-model validation — see the standing risk above.
- **Next best action:** unchanged — complete `real-model-validation` on the session machine.

### 2026-07-29 — agent surfaces added

- **Goal:** define an assistant that can run this project in VS Code, for both GitHub Copilot and
  the Continue extension.
- **Completed:**
  - `bmad/` doctrine layer: five agent charters, three workflows, two checklists.
  - `.github/`: `copilot-instructions.md`, six `.agent.md` custom agents with handoff chains,
    six `.prompt.md` slash commands, three scoped `.instructions.md` files.
  - `.continue/`: `config.yaml` (local Ollama models, 11 always-on rules, the same six slash
    commands) and five rule files.
  - `.vscode/`: settings, tasks wrapping the Makefile targets, extension recommendations.
  - Root harness files: `AGENTS.md`, `Makefile`, `feature_list.json`, this file.
  - `tools/verify_package.py`: nine checks, including a new one covering the agent surfaces.
- **Verification run:** `make verify` → exit 0, all checks pass. `make demo` → exit 0.
- **Evidence:** pasted in `feature_list.json` under items `harness-core`, `demo-assistant`,
  `teaching-parts-1-4` and `agent-surfaces`.
- **Known risks:** the three above. Note especially that `make demo` passing does **not** mean a
  model works.
- **Next best action:** on the machine that will be used in the session, run
  `make eval MODEL=llama3.1:8b` and complete item `real-model-validation`. Then walk
  `bmad/checklists/session_readiness.md`.

<!-- Add a new entry ABOVE this line each session. Do not edit earlier entries. -->

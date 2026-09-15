---
name: Project map
alwaysApply: true
---

# UNEVOC Harness Engineering Package

Read `AGENTS.md` at the repository root before acting. It is the instructions subsystem of this
project's harness and takes precedence over anything inferred from the code.

An offline teaching package on prompt → skill → harness → loop engineering, plus a working local
document assistant, for UNESCO UNEVOC Magdeburg. Four parts: `part1_timeline/` (concepts),
`part2_teaching/` (deck, cheatsheet, runbooks, minimal harness), `part3_worked_example/`
(semi-agent vs agent), `part4_unesco_brief/` (assistants, agents, knowledge bases, demo assistant).

Everything must be accurate, pedagogically sequenced and **runnable**. Decorative content is a
defect.

## Session protocol

1. Read `PROGRESS.md` — the truth about where things stand, not the chat history.
2. Read `feature_list.json`; take the highest-priority `not_started` item.
3. Set **exactly one** item to `in_progress`.
4. Run `make verify` to establish the starting state.
5. At the end, append a session record to `PROGRESS.md`. Do not rewrite earlier entries.

## Roles

Charters are in `bmad/agents/`. Adopt one explicitly when asked: `@curator` (corpus hygiene),
`@librarian` (assistant operations), `@author` (teaching material), `@qa` (verification,
read-only), `@packager` (release). Workflows are in `bmad/workflows/`.

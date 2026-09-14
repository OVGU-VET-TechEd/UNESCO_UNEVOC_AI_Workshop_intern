# AGENTS.md — UNEVOC Harness Engineering Package

This file is the **instructions subsystem** of this repository's harness. It is read first by
every agent surface: GitHub Copilot in VS Code (`.github/`), Continue (`.continue/`), Claude Code
(`.claude/agents/` symlinks to the same definitions), and any human joining the project.

It is a **map, not an encyclopaedia**. If a section grows past a screenful, move it into `bmad/`
and link to it from here.

---

## Project

An offline teaching package on prompt → skill → harness → loop engineering, plus a working
document assistant, prepared for UNESCO UNEVOC Magdeburg. Everything in it must be **accurate,
pedagogically sequenced and runnable**. Decorative content is a defect.

Four parts: `part1_timeline/` (concepts), `part2_teaching/` (deck, cheatsheet, runbooks, minimal
harness), `part3_worked_example/` (semi-agent vs agent), `part4_unesco_brief/` (assistants, agents,
knowledge bases, and the demo assistant).

## Stack

- Runtime: Python 3.9+ — the harness core uses **only the standard library**
- Inference: Ollama at `http://127.0.0.1:11434`, typically `llama3.1:8b` and `qwen2.5:7b`
- Third-party packages: `pdfplumber`, `matplotlib`, `reportlab` — document work only
- No build system beyond `make`

## Start here, every session

1. Read `PROGRESS.md`. It is the truth about where things stand — not the chat history.
2. Read `feature_list.json`. Take the highest-priority item with status `not_started`.
3. Set **exactly one** item to `in_progress`. Never more than one.
4. Run `make verify`. If it fails before you start, fix that first and say so.

## Hard constraints (non-negotiable)

- **Offline only.** No code in this repository may reach any network endpoint other than
  `127.0.0.1:11434`. `make verify` enforces this and will fail the build.
- **Never write into `part4_unesco_brief/demo_assistant/corpus/` by hand.** It is a build
  artefact of `anonymise.py`. Edit `corpus_raw/`, then re-run the scrubber.
- **Never index a corpus without a human having read `anonymisation_report.md`.** The scrubber
  is a redaction aid, not a compliance tool, and it cannot catch indirect identifiers.
- **Never mark an item `passing` without pasting `make verify` output as evidence** into the
  `evidence` field of `feature_list.json`.
- **Never present mock output as model output.** `tools/mock_ollama.py` returns canned text.
- Do not delete or rewrite `PROGRESS.md` history. Append.

## Accuracy rules for teaching content

- Claims about the UNESCO frameworks use UNESCO's own progression labels: **Acquire / Deepen /
  Create** (teachers) and **Understand / Apply / Create** (students). "AI-literate" and
  "AI-enhanced educator" are **not** UNESCO terms and must not be presented as such.
- LiaScript quiz syntax: single choice `[( )]` / `[(X)]`, multiple choice `[[ ]]` / `[[X]]`.
  Sources that state this the other way round are wrong; `make verify` checks it.
- Retrieval thresholds in `ask.py` are corpus-specific. Any change must be justified by an
  `eval_kb.py` run, and the run must be quoted.
- If a claim cannot be verified from a cited source, say so explicitly in the text. Do not
  invent, and do not quietly soften. Flagging beats guessing.

## Verification commands

`make verify` is the definition of done. It exits non-zero on failure.

| Command | What it checks |
|---|---|
| `make verify` | syntax · JSON · structure · offline-only · LiaScript · anonymisation leaks · knowledge base integrity · Markdown links |
| `make kb` | rebuilds the demo knowledge base from `corpus/` |
| `make eval` | runs the assistant against `eval_questions.json` and reports three rates |
| `make demo` | end-to-end smoke test of Parts 2, 3 and 4 against the mock server |
| `make clean` | removes generated artefacts |

## Definition of done

An item is done when **`make verify` exits 0** AND the evidence is recorded in
`feature_list.json`. An agent's own opinion that the work looks finished does not count.

Where the change touches the demo assistant, `make eval` must also be run and its three rates
recorded — a change that improves phrasing while lowering the refusal rate is a regression.

## The five agents

Definitions live in `bmad/agents/` and are the single source of truth. `.github/agents/` and
`.continue/` are thin adapters over them.

| Agent | Owns | May write to |
|---|---|---|
| `@curator` | corpus hygiene: raw → anonymise → review → index | `corpus_raw/`, then runs the pipeline |
| `@librarian` | assistant operations: ask, evaluate, tune thresholds | `eval_questions.json`, `ask.py` thresholds |
| `@author` | teaching material: decks, cheatsheet, runbooks, use cases | Markdown and HTML under `part1`–`part4` |
| `@qa` | verification only — **read-only, never edits** | nothing |
| `@packager` | clean-room rebuild and distribution | `dist/` |

Only one agent works at a time, and only on the one `in_progress` item.

## End of session

Append a session record to `PROGRESS.md`: goal, completed, verification run and its result,
evidence path, known risks, and the single next best action.

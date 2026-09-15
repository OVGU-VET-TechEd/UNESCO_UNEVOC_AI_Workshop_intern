# Copilot instructions — UNEVOC Harness Engineering Package

VS Code loads this file automatically for every chat request in this workspace. It is a **map**.
The doctrine lives elsewhere; follow the links.

**Read [`../AGENTS.md`](../AGENTS.md) first.** It is the instructions subsystem of this
repository's harness and it takes precedence over anything inferred from the code.

## What this repository is

An offline teaching package on prompt → skill → harness → loop engineering for UNESCO UNEVOC
Magdeburg, plus a working local document assistant. Everything must be accurate, pedagogically
sequenced and **runnable**. Decorative content is a defect.

## Non-negotiables

1. **Offline only.** No code may reach any endpoint other than `127.0.0.1:11434`.
   `make verify` fails the build if it does. Do not add an SDK, a cloud client, or a CDN link.
2. **The harness core uses the standard library only.** `pdfplumber`, `matplotlib` and
   `reportlab` are for document work. Do not add dependencies to state, verification, logging or
   the Ollama client.
3. **`make verify` is the definition of done.** Never report work as complete without running it
   and pasting the output. Your own assessment that the code looks right does not count.
4. **Never edit `part4_unesco_brief/demo_assistant/corpus/`.** It is a build artefact of
   `anonymise.py`. Edit `corpus_raw/` and re-run the pipeline.
5. **Never index a corpus before a human has read `anonymisation_report.md`.** Stop and ask.
6. **Never present `tools/mock_ollama.py` output as model output.** It returns canned text.
7. **One item `in_progress` at a time** in `feature_list.json`.

## Writing rules

- UNESCO progression levels are **Acquire / Deepen / Create** (teachers) and
  **Understand / Apply / Create** (students). "AI-literate" / "AI-enhanced educator" are not
  UNESCO terms.
- LiaScript: single choice `[( )]` / `[(X)]`, multiple choice `[[ ]]` / `[[X]]`, speaker notes
  `--{{n}}--` under every slide.
- If you cannot verify a claim from a source, **say so in the text**. Do not invent a plausible
  date, figure or quotation.
- Comment code so a non-programmer can follow the control flow. That is a requirement of this
  project, not a style preference.

## Commands

`make help` lists them. The ones that matter: `make verify`, `make demo`, `make eval`,
`make corpus`, `make kb`.

## Agents and slash commands

Six custom agents in [`agents/`](agents), each with a charter in
[`../bmad/agents/`](../bmad/agents). Switch with the agents dropdown, or chain them with the
handoff buttons that appear after a response.

| Agent | For |
|---|---|
| `Curator` | corpus hygiene — raw → anonymise → review → index |
| `Librarian` | assistant operations — ask, evaluate, tune thresholds |
| `Author` | teaching material — decks, cheatsheet, runbooks, use cases |
| `QA` | verification only, read-only, never edits |
| `Packager` | clean-room rebuild and release |
| `UNEVOC Lead` | orchestrator — picks the right agent and runs the workflows |

Slash commands are in [`prompts/`](prompts): `/verify`, `/refresh-corpus`, `/eval-assistant`,
`/new-teaching-section`, `/session-prep`, `/release`.

## Workflows

[`../bmad/workflows/`](../bmad/workflows): W1 corpus refresh, W2 session prep, W3 release. Each
has a human checkpoint that must not be automated away.

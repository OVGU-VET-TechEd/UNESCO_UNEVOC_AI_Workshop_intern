# AGENTS.md — TEMPLATE

<!--
  Copy this file to the root of your own repository and fill in the angle-bracket
  parts. Keep it around 100 lines. It is a MAP, not an encyclopaedia: if a section
  grows past a screenful, move it into docs/ and link to it from here.

  Pattern from the Learn Harness Engineering template library:
  https://walkinglabs.github.io/learn-harness-engineering/en/resources/templates/

  Use the filename AGENTS.md for Codex and most agents; CLAUDE.md for Claude Code.
  The structure is the same either way.
-->

## Project

<One paragraph. What does this repository produce, and who consumes the output?>

## Stack

- Runtime:        <python 3.11 / node 20 / ...>
- Model:          <gemma3:12b> via Ollama at <http://127.0.0.1:11434>
- Key libraries:  <pdfplumber, matplotlib, ...>
- Export/build:   <liaex --format scorm1.2 / make build / ...>

## Start here, every session

1. Read `PROGRESS.md`. It is the truth about where things stand.
2. Read `feature_list.json`. Take the highest-priority item with status `not_started`.
3. Set exactly ONE item to `in_progress`. Never more than one.
4. Run the environment check: `<./init.sh>`. If it fails, fix that before anything else.

## Hard constraints (non-negotiable)

- Never call any network endpoint other than <http://127.0.0.1:11434>.
- Never create or edit files outside <./content> and <./build>.
- Never mark an item `passing` without pasting the verification output as evidence.
- <Add the rule that exists only in your head. That is the one worth writing down.>

## Verification commands

<Every command here must exit non-zero on failure. This section is the highest-value
 part of the file — a definition of done that cannot be argued with.>

- Structure check:  `<python tools/check.py FILE>`
- Build check:      `<make build>`
- Full check:       `<make verify>`   # runs all of the above

## Definition of done

An item is done when `<make verify>` exits 0 AND the evidence is recorded in
`feature_list.json`. The agent's own opinion that the work looks finished does not
count.

## End of session

Update `PROGRESS.md` with: what is done, what is in progress, what is blocked, which
verification was run, and the single next best action.

# Harness Engineering — One-Page Cheatsheet

*UNESCO UNEVOC Centre Magdeburg / OVGU · handout for students and staff · print A4*

---

## The four levels (cumulative — each keeps the ones below it)

| # | Level | You edit… | It fixes… | Common since |
|---|---|---|---|---|
| 1 | **Prompt Engineering** | the prompt string | the model answering the wrong question | 2020–2022 |
| 2 | **Skill Engineering** | the skill file (`SKILL.md`, agent file) | re-explaining the same conventions every session | 2023–2025 |
| 3 | **Harness Engineering** | the harness: `AGENTS.md`, tools, state file, verification command | "done" that isn't done; losing everything between sessions | 2025 |
| 4 | **Loop Engineering** | the evaluation signal and the stop condition | you being the bottleneck — nothing moves unless you type | 2026 |

---

> **Simplicity Statement — Harness Engineering**
> A harness does not make the model smarter. It gives a fixed model a place to keep state, a way to
> check its own work, and rules for when to stop. Everything else in this package is one worked
> example of that idea.

---

## The five subsystems of a harness

**Instructions** · **Tools** · **Environment** · **State** · **Feedback**

Missing any one of them means an incomplete harness. *Feedback is the cheapest to add and returns the
most.* If it is not model weights, it is harness.

---

## `AGENTS.md` — minimal skeleton

Keep it a map, not an encyclopaedia. Around 100 lines. If it grows past that, split it into `docs/`
and link out.

```markdown
# AGENTS.md

## Project
One paragraph: what this repo produces and who consumes it.

## Stack
- Runtime:            python 3.11 / node 20
- Model:              gemma3:12b via Ollama at http://127.0.0.1:11434
- Export toolchain:   liaex --format scorm1.2

## Start here, every session
1. Read `PROGRESS.md`.
2. Read `feature_list.json`; pick the highest-priority `not_started` item.
3. Set exactly ONE item to `in_progress`. Never more than one.

## Hard constraints (non-negotiable)
- Never call a network endpoint other than 127.0.0.1:11434.
- Never edit files outside ./content and ./build.
- Never mark an item `passing` without pasting the verification output as evidence.

## Verification commands
- Structure check:  python tools/check_module.py content/<id>.md
- Export check:     liaex --format scorm1.2 content/<id>.md
- Full check:       make verify        # runs both, exits non-zero on failure

## Definition of done
An item is done when `make verify` exits 0 AND the evidence is recorded in feature_list.json.

## End of session
Update `PROGRESS.md`: what is done, what is in progress, what is blocked, next best action.
```

---

## `feature_list.json` — minimal skeleton

```json
{
  "features": [
    {
      "id": "mod-hydraulics-01",
      "priority": 1,
      "area": "content",
      "title": "Hydraulic safety — introductory module",
      "user_visible_behavior": "Learner sees 6 slides, 1 quiz, and can export to SCORM 1.2.",
      "status": "not_started",
      "verification": [
        "make verify content/mod-hydraulics-01.md",
        "open the SCORM package and confirm the quiz records a score"
      ],
      "evidence": "",
      "notes": ""
    }
  ]
}
```

**Status values:** `not_started` → `in_progress` → `passing`, or `blocked`.
**Rule:** only ONE item may be `in_progress` at any time.

---

## `PROGRESS.md` — minimal skeleton

```markdown
## Current verified state
- Repository root:        ~/microcredential-factory
- Standard start command: ./init.sh
- Standard verify command: make verify
- Highest-priority unfinished item: mod-hydraulics-01
- Current blocker:        none

## Session record — 2026-07-27
- Goal:              draft mod-hydraulics-01
- Completed:         slides 1–4 drafted
- Verification run:  make verify → FAILED (quiz block missing)
- Evidence:          logs/verify-2026-07-27.txt
- Next best action:  add the quiz block, re-run make verify
```

---

## Harness health checklist

Run this against any AI workflow before trusting it unattended.

- [ ] **State persists.** Kill the process mid-run and restart it — does it know what was already done?
- [ ] **Verification exists.** Is there a command that returns pass/fail, independent of the model's own opinion?
- [ ] **Stop condition defined.** Is there a written rule for when the work is finished — not "when it feels done"?
- [ ] **Logs observable.** Can a colleague reconstruct what happened, and why, from files alone?
- [ ] **Instructions are on disk.** Are the conventions written in the repo, not in someone's head?
- [ ] **Environment is reproducible.** Does one command set the machine up from scratch?
- [ ] **Generator ≠ evaluator.** Is the thing that judges the work different from the thing that made it?
- [ ] **Scope is bounded.** Exactly one work item `in_progress`; retries capped at N.

*Four or fewer boxes ticked: do not run it unattended.*

---

## Sources

Learn Harness Engineering (Walking Labs) — <https://walkinglabs.github.io/learn-harness-engineering/en/> ·
Meta-Harness, Lee, Nair, Zhang, Lee, Khattab & Finn, COLM 2026 — <https://yoonholee.com/meta-harness/> ·
UNESCO AI competency frameworks for teachers and students (2024) — <https://www.unesco.org/en/articles/ai-competency-framework-teachers>

**UNESCO alignment.** This sheet is an *Acquire*/*Deepen*-level aid under the UNESCO AI competency
framework for teachers (aspects: AI foundations and applications; AI pedagogy). The health checklist
operationalises the framework's human-agency and accountability principles: each box is a concrete
form of the requirement that a teacher remain accountable for, and able to critically evaluate, what
an AI system produces. UNESCO's progression levels are Acquire / Deepen / Create for teachers and
Understand / Apply / Create for students.

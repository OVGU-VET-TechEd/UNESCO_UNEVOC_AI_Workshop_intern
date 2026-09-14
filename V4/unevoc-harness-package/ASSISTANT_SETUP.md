# Running this project with an assistant in VS Code

This package ships a **project assistant**: a set of role agents, slash commands and rules that
let Copilot or Continue operate this repository safely — refresh the corpus, evaluate the
assistant, draft teaching material, verify, and release.

Both surfaces are configured. **You do not need both.** Pick one.

| | GitHub Copilot | Continue |
|---|---|---|
| Config | `.github/` | `.continue/` |
| Models | Copilot's hosted models | **your local Ollama models** |
| Role agents | six, in the agents dropdown | adopted by slash command |
| Handoff buttons between roles | yes | no — the chain is in the prompt text |
| Works fully offline | no | **yes** |

For UNEVOC's offline requirement, **Continue is the surface that matches the package's own
constraint**: the teaching material argues that nothing should leave the machine, and Continue
with Ollama honours that. Copilot gives a better multi-agent experience (handoffs, per-agent tool
restrictions) at the cost of sending your prompts to a hosted model. If you use Copilot here, be
straight with the room about that difference — it is a good teaching moment, not an embarrassment.

---

## The structure, and why it is shaped this way

```text
AGENTS.md                      the map — read by every surface and every human
bmad/                          DOCTRINE — surface-independent
  agents/*.md                    role charters: purpose, write-scope, stop conditions
  workflows/W*.md                W1 corpus refresh · W2 session prep · W3 release
  checklists/*.md                definition of done · session readiness
     │
     ├── .github/               COPILOT ADAPTER
     │     copilot-instructions.md      always loaded, links to AGENTS.md
     │     agents/*.agent.md            6 custom agents, with handoff chains
     │     prompts/*.prompt.md          6 slash commands
     │     instructions/*.instructions.md  auto-applied by file glob
     │
     └── .continue/            CONTINUE ADAPTER
           config.yaml                  local models, 11 always-on rules, 6 slash commands
           rules/*.md                   the same doctrine, Continue's format

.vscode/                       settings, tasks wrapping the Makefile, extension recommendations
Makefile                       the verification commands — one definition of done, not four
feature_list.json              the work, machine-readable. ONE item in_progress at a time
PROGRESS.md                    state that outlives the session
tools/verify_package.py        `make verify` — nine checks, the arbiter of "done"
```

**The rule that keeps this from rotting:** doctrine changes are made in `bmad/` or `AGENTS.md`
first, and the adapters are updated to point at them. Never the other way round. Otherwise the
rule "never index a corpus before a human reads the report" gets written three times, drifts, and
means three different things.

This is itself an instance of the package's own subject matter. `AGENTS.md` and `bmad/` are the
**instructions** subsystem; `feature_list.json` and `PROGRESS.md` are **state**; `make verify` is
**feedback**; the agent `tools:` lists are **tools**; `make init` is **environment**. Five
subsystems, as taught in Part 2.

---

## The six agents

Charters in `bmad/agents/`; Copilot versions in `.github/agents/`.

| Agent | Owns | May write to | Refuses to |
|---|---|---|---|
| **Curator** | corpus hygiene: raw → anonymise → review → index | `corpus_raw/`, `names.txt` | index anything before a human reads the anonymisation report; claim a document *is* anonymised |
| **Librarian** | assistant operations: ask, evaluate, tune | `eval_questions.json`, thresholds in `ask.py` | report a blended accuracy figure; change two constants at once |
| **Author** | all teaching prose | Markdown/HTML in `part1`–`part4` | assert anything about a source without re-opening it; use non-UNESCO terminology |
| **QA** | verification | **nothing — read-only** | fix what it finds |
| **Packager** | clean-room rebuild and release | `dist/` | start before QA has reported PASS |
| **UNEVOC Lead** | orchestration and routing | coordinates only | let two items be `in_progress` |

**QA is read-only on purpose.** The package's central reliability rule is generator/evaluator
separation. A QA agent that fixes what it finds has become the generator, and its verdict stops
carrying information. It has no `edit` tool and is instructed not to ask for one.

### Handoff chains (Copilot)

Handoff buttons appear under a completed response, so the workflow is a click rather than a thing
you remember:

```text
Curator ──▶ Librarian ──▶ QA ──▶ Packager
   │                       │
   └───────────────────────┴──▶ (back to Curator or Author on failure)

Author ─────────────────▶ QA
UNEVOC Lead ────────────▶ QA        (opens every session by establishing state)
```

Continue has no handoff mechanism, so each slash command names the next step in its text instead.

---

## The six slash commands

Identical names on both surfaces.

| Command | Runs as | Does |
|---|---|---|
| `/verify` | QA | `make verify` + `make demo`, reports verbatim with the limitations paragraph |
| `/refresh-corpus` | Curator | workflow W1, stopping at the human checkpoint |
| `/eval-assistant` | Librarian | `make eval`, diagnoses which of the three rates is wrong |
| `/new-teaching-section` | Author | drafts to the editorial standard, re-fetching sources |
| `/session-prep` | UNEVOC Lead | workflow W2 on *this* machine, forbidding the mock |
| `/release` | UNEVOC Lead | workflow W3, ending in an archive verified from a fresh extraction |

---

## Setup — Copilot

1. Install **GitHub Copilot** and **GitHub Copilot Chat**.
2. Open this folder as the workspace root. That is required: `.github/` is discovered relative to
   the workspace, not to the file you have open.
3. Open the Chat view. The agents dropdown should list Curator, Librarian, Author, QA, Packager
   and UNEVOC Lead.
4. Type `/` — the six commands should appear.

✅ **Check:** select **UNEVOC Lead**, send `/verify`. You should see `make verify` run and a PASS
report ending with the limitations paragraph.

> **If the agents do not appear:** right-click in the Chat view → **Diagnostics** to see which
> customization files were loaded and any errors. The usual cause is opening a parent folder
> instead of this one.
>
> **A note on tool names.** The `tools:` lists in the agent frontmatter use VS Code's custom-agent
> tool identifiers as of July 2026. These change between releases. VS Code **ignores** a tool it
> does not recognise rather than erroring, so a stale name degrades an agent quietly rather than
> breaking it. If an agent seems unable to run commands, open its `.agent.md`, use
> **Configure Tools**, and re-pick from the live list.

---

## Setup — Continue (fully offline)

1. Install the **Continue** extension (`continue.continue`).
2. Make sure Ollama is running and both models are pulled — see
   `part2_teaching/RUNBOOK_macOS.md` or `RUNBOOK_Windows.md`, steps 1–3.
3. Open this folder as the workspace root. Continue loads `.continue/config.yaml` automatically.
4. Open the Continue panel. The model dropdown should list **Local (autodetect)** plus the named
   local models; typing `/` should offer the six commands.

✅ **Check:** send `/verify`. You should see `make verify` run locally, with no network traffic
leaving the machine.

The config uses Ollama's `AUTODETECT` so Continue lists what is actually installed rather than
what someone assumed — the same principle the package's own scripts follow by reading
`ollama list` / `/api/tags`.

> **If a model is missing:** `ollama list` is the source of truth. The explicit entries in
> `config.yaml` are convenience; delete any you have not pulled.
>
> **If autocomplete produces garbage:** the autocomplete role needs a fill-in-the-middle model.
> `qwen2.5-coder:1.5b` is configured for it. Do not point autocomplete at a chat model.

---

## First session, whichever surface

```text
1.  Open the workspace.
2.  /verify                        establish the starting state. Nothing else until this passes.
3.  Read PROGRESS.md               it names the highest-priority unfinished item.
4.  Switch to the owning agent.    One item in_progress. Only one.
5.  Do the work.
6.  /verify                        paste the output into feature_list.json as evidence.
7.  Append a session record to PROGRESS.md before you close the window.
```

Step 7 is the one people skip, and it is the one that makes step 3 possible next time.

---

## What the assistant will refuse to do

These refusals are the point, not friction. Each is written into the agent charters, the
instruction files and the Continue rules, so they hold on both surfaces.

- **Index a corpus before a human has read `anonymisation_report.md`.** Not for small changes,
  not for releases, not when the agent is confident.
- **Edit `corpus/`, `kb.json` or `anonymisation_report.md`.** They are build artefacts.
  `.vscode/settings.json` also marks them read-only in the editor, so a stray manual edit is
  blocked before it starts.
- **Claim a document is anonymised.** The scrubber removes identifiers with a predictable shape.
  It cannot find names it was not given and cannot detect indirect identifiers at all. The agent
  reports what was removed; the human judges.
- **Add a network call to anything other than `127.0.0.1:11434`.** `make verify` fails the build.
- **Mark work done without `make verify` output.** Its own opinion does not count.
- **Let QA fix what QA found.**
- **Present mock output as model output.**
- **Have two items `in_progress`.**

---

## Adapting this for another project

The structure transfers; the content does not. To reuse it:

1. Copy `AGENTS.md`, `bmad/`, `.github/`, `.continue/`, `.vscode/`, `Makefile`,
   `tools/verify_package.py`, `feature_list.json`, `PROGRESS.md`.
2. **Rewrite `tools/verify_package.py` first.** It is the definition of done, and a copied
   verification script that checks the wrong things is worse than none. Delete every check that
   does not apply and add the ones that do. A check you cannot run is not a standard.
3. Re-cut the roles. Five is not a magic number — this project's set differs from a generic
   software one because corpus hygiene and assistant evaluation are real jobs here and an
   architect role would have had nothing to do.
4. Keep three things unchanged: **QA is read-only**, **one item `in_progress`**, and
   **`make verify` is the only thing that makes something done**.

Blank skeletons of the three state files are in `templates/`.

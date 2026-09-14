# Harness Engineering — UNESCO UNEVOC Magdeburg demonstration package

An offline teaching package on prompt → skill → harness → loop engineering, built for university
lecturers, TVET instructors and academic researchers. Every executable part runs against a **local
Ollama model on 127.0.0.1**. There is no cloud API key anywhere in this package and no code that
could use one.

---

## What is in here

```text
unevoc-harness-package/
├── 00_INDEX.md                            ← you are here
├── ASSISTANT_SETUP.md                     run this project with an assistant in VS Code
├── AGENTS.md                              the harness instructions subsystem — read by everything
├── Makefile                               make verify · demo · eval · corpus · kb · package
├── feature_list.json                      the work, machine-readable. ONE item in_progress
├── PROGRESS.md                            state that outlives the session
│
├── bmad/                                  DOCTRINE — surface-independent
│   ├── agents/                            five role charters
│   ├── workflows/                         W1 corpus refresh · W2 session prep · W3 release
│   └── checklists/                        definition of done · session readiness
├── .github/                               COPILOT ADAPTER — instructions, 6 agents, 6 commands
├── .continue/                             CONTINUE ADAPTER — local models, rules, same 6 commands
├── .vscode/                               settings, tasks, extension recommendations
│
├── part1_timeline/
│   └── PART1_four_levels_timeline.md      the four levels, table + prose + Simplicity Statement
│
├── part2_teaching/
│   ├── FILE_A_harness_engineering_liascript.md   LiaScript deck, 4 sections + quizzes + speaker notes
│   ├── FILE_B_cheatsheet.md               one-page handout, Markdown
│   ├── FILE_B_cheatsheet.html             same handout, self-contained, print-friendly
│   ├── RUNBOOK_macOS.md                   copy-paste zsh setup, 10 numbered steps with ✅ checks
│   ├── RUNBOOK_Windows.md                 the same in PowerShell
│   └── file_d_min_harness/
│       ├── min_harness.py                 the smallest complete harness: state + verify + retry + log
│       └── README.md                      what to point at while you run it
│
├── part3_worked_example/
│   ├── README.md                          ← the most important file in the package
│   ├── common.py                          shared: Ollama client, PDF→Markdown, chart, report builder
│   ├── make_sample_pdfs.py                creates three sample input PDFs
│   ├── semi_agent.py                      VARIANT A — fixed pipeline, human checkpoint
│   ├── agent.py                           VARIANT B — control loop, self-terminating
│   ├── requirements.txt
│   └── input_pdfs/                        three sample PDFs (replace with your own)
│
├── part4_unesco_brief/                    ← responds directly to the UNESCO brief
│   ├── 00_PART4_INDEX.md                  coverage table + a 2-hour session plan
│   ├── A_definitions_...md                assistants, agents, knowledge bases — precisely
│   ├── B_unevoc_use_cases.md              document review · knowledge management ·
│   │                                      project monitoring · training development
│   ├── C_pilot_selection_worksheet.md     ten-question scoring sheet, print one per candidate
│   ├── D_liascript_deck_assistants.md     the deck for that session
│   └── demo_assistant/                    a working offline document assistant
│       ├── README.md                      ← read before running anything
│       ├── make_corpus.py                 eight synthetic documents
│       ├── anonymise.py                   scrub identifiers, write a report for human review
│       ├── kb_build.py                    documents → passages → kb.json
│       ├── ask.py                         retrieve → ground → verify → cite, or refuse
│       ├── eval_kb.py                     fixed question set, three separate numbers
│       └── corpus_raw/ corpus/ kb.json    shipped pre-built so you can read them
│
├── part5_self_improving/                  ← the interactive page + layer 5
│   ├── LEARN_the_five_layers.html         open in a browser: six layers, live prompt stack
│   ├── wiki_agent.py                      an agent that writes its own SKILL.md
│   └── README.md
│
├── templates/
│   ├── AGENTS.md                          fill-in skeleton — instructions subsystem
│   ├── feature_list.json                  fill-in skeleton — scope and verification
│   └── PROGRESS.md                        fill-in skeleton — state subsystem
│
└── tools/
    ├── mock_ollama.py                     fake server so the demos run with no model installed
    └── verify_package.py                  `make verify` — nine checks, the arbiter of "done"
```

---

## File-by-file: what each one is for

| File | For whom | Purpose |
|---|---|---|
| `part1_timeline/PART1_four_levels_timeline.md` | staff | Background reading. The four levels with definition, unit of iteration, failure mode fixed, a worked example in the Ollama/DGX/LiaScript stack, and dates. Contains the Simplicity Statement and the UNESCO mapping, including one correction to the terminology in common circulation. |
| `part2_teaching/FILE_A_..._liascript.md` | both | The lecture. Four sections, fragment reveals, a quiz after each section, a five-question closing quiz, and speaker notes under every slide. Render it at <https://liascript.github.io/course/?URL-of-this-file>. |
| `part2_teaching/FILE_B_cheatsheet.md` / `.html` | both | The handout. Four-level table, Simplicity Statement, three template skeletons, and an eight-item harness health checklist. Print the HTML: one A4 sheet, both sides. |
| `part2_teaching/RUNBOOK_macOS.md` | staff | Setup, ten numbered steps, each ending in a ✅ check. Ollama, two models, REST API verification, venv, both demos, open the report. |
| `part2_teaching/RUNBOOK_Windows.md` | staff | The same in PowerShell, including the `Set-ExecutionPolicy` fix that trips up most Windows setups. |
| `part2_teaching/file_d_min_harness/` | both | The smallest complete example: three topics, three ground rules, bounded retry, persistent state, plain-language log. Switch models with `--model`. Under two minutes on a laptop CPU. |
| `part3_worked_example/README.md` | both | Which lines of code are the harness and which are the model call. **The single most important pedagogical point in the package.** |
| `part3_worked_example/semi_agent.py` | both | Variant A: fixed sequence, human confirms before the report, no autonomous retry. |
| `part3_worked_example/agent.py` | both | Variant B: the model proposes each next action, the harness validates it, runs it, verifies the output, and stops itself when every PDF appears in the report. |
| `templates/` | staff | Copy into your own repository and fill in. Blank skeletons, no project-specific content. |
| `part4_unesco_brief/A_definitions_...md` | both | Eleven terms defined precisely — model, context window, assistant, tool, knowledge base, embedding, RAG, agent, harness, hallucination, refusal — plus a confused-pairs table and a "which one do you need" decision table. |
| `part4_unesco_brief/B_unevoc_use_cases.md` | staff | Document review, knowledge management, project monitoring and training development, each to the same eight headings, each with a pilot spec and a stated failure criterion. |
| `part4_unesco_brief/C_pilot_selection_worksheet.md` | staff | Ten scored questions for choosing a pilot, plus five questions to ask any vendor. Print one per candidate. |
| `part4_unesco_brief/D_liascript_deck_assistants.md` | both | The deck for the assistants/agents/knowledge-bases session. Four sections, quizzes, facilitator notes. |
| `part4_unesco_brief/demo_assistant/` | both | A working offline document assistant: anonymise → build knowledge base → ask with citations → refuse when uncovered → evaluate. Four of its five programs contain no AI at all, which is the lesson. |
| `ASSISTANT_SETUP.md` | staff | How to run this project with a project assistant in VS Code — six role agents and six slash commands, configured for both GitHub Copilot and Continue. Continue is the offline surface. |
| `AGENTS.md` · `bmad/` | staff | The harness that operates this repository: role charters, three workflows, two checklists, and the rule that QA is read-only. An instance of the package's own subject matter. |
| `Makefile` · `tools/verify_package.py` | staff | `make verify` is the definition of done: syntax, JSON, structure, offline-only, LiaScript, anonymisation leaks, knowledge base integrity, links, agent surfaces. |
| `part5_self_improving/LEARN_the_five_layers.html` | both | **The interactive page.** Six layers from a bare prompt to a self-improving agent, with a prompt inspector that grows as you advance. Self-contained: open it with the network off. Covers tokens, weights and the context budget at layer 0, then prompting → skills → harness → loop → self-improvement, each with UNEVOC applications and runnable Python. |
| `part5_self_improving/wiki_agent.py` | staff | A working WikiSkill-style loop: the agent writes its own skill file, keeps an append-only wiki of what it learned, and rolls back changes that score worse. `make evolve`. |
| `tools/mock_ollama.py` | staff | Runs the whole package with no model installed, for laptops that cannot host one. Also serves fake embeddings so the Part 4 knowledge-base path can be demonstrated. Returns canned text — never present its output as model output. |

---

## Facilitator walkthrough — a 90-minute session

Run through the runbook **before** the room arrives, so the models are already downloaded.

| # | Minutes | Do this | With this file |
|---|---|---|---|
| 0 | −30 | Set up the demo machine. Get to the end of Step 8 of the runbook and confirm both demos run. | `RUNBOOK_macOS.md` or `RUNBOOK_Windows.md` |
| 1 | 0–5 | Hand out the cheatsheet. Point at the four-level ladder, say the levels are cumulative, and stop there. | `FILE_B_cheatsheet.html` (printed) |
| 2 | 5–20 | Section 1 of the deck: why prompting alone breaks down. Run the section quiz. | `FILE_A` §1 |
| 3 | 20–40 | Section 2: what a harness is. The five subsystems, the repository as system of record, the verification gap. Show the blank templates on screen while you talk about instructions and state. | `FILE_A` §2 + `templates/` |
| 4 | 40–50 | **Run File D live.** Three topics, three rules, watch a rejection and a retry happen on screen. Then run it again and watch it skip everything — that is the state file. | `file_d_min_harness/` |
| 5 | 50–60 | Section 3: harness vs. loop, the Meta-Harness search loop, the four silent costs. Run the section quiz. | `FILE_A` §3 |
| 6 | 60–75 | **Run Part 3 live.** `semi_agent.py --pause` first, so the room sees a file appear after every step and a real human decision point. Then `agent.py`. | `part3_worked_example/` |
| 7 | 75–85 | Open `agent_log.md` and read it aloud. Find one place where the harness overrode the model. Then open `agent.py`, search for `call_ollama`, and count the hits: two. | `part3_worked_example/README.md` |
| 8 | 85–90 | Closing quiz. Question 5 alone carries the argument. Close on the Simplicity Statement, which is on their handout. | `FILE_A` closing quiz |

**If you only have 30 minutes:** step 1, step 4, step 7, closing question 5.

**Part 4 is a separate 2-hour session** aimed at the UNESCO brief itself — assistants, agents and
knowledge bases, the four UNEVOC use cases, and a live document assistant. Its own plan is in
`part4_unesco_brief/00_PART4_INDEX.md`. It shares the runbooks in Part 2 for setup, and it can be
delivered before or after the harness session. That sequence still
lands the whole argument.

**For a shorter, self-guided option:** hand people
`part5_self_improving/LEARN_the_five_layers.html` and let them work through the six layers at their
own pace. It covers the same progression as steps 2–7 above and needs no facilitator, no model and
no network.

**Follow-up task to set:** take `templates/AGENTS.md` and `templates/feature_list.json`, fill them in
for one real workflow in your own department, and score it against the eight-item health checklist on
the cheatsheet. Anything scoring four or fewer should not be run unattended.

---

## Sources, and what could and could not be verified

Everything asserted in this package traces to one of four sources. All four were fetched and read
while the package was written; nothing here is paraphrased from memory.

- **Learn Harness Engineering** (Walking Labs) — a project-based course on the environments, state,
  verification and control systems that make coding agents reliable. Lectures 01, 02 and 13 and the
  template library are the primary references for Parts 1 and 2.
  <https://walkinglabs.github.io/learn-harness-engineering/en/>
- **Meta-Harness: End-to-End Optimization of Model Harnesses** — Yoonho Lee, Roshen Nair, Qizheng
  Zhang, Kangwook Lee, Omar Khattab, Chelsea Finn. COLM 2026.
  <https://yoonholee.com/meta-harness/> · <https://arxiv.org/abs/2603.28052> ·
  <https://github.com/stanford-iris-lab/meta-harness>
- **UNESCO AI competency framework for teachers** (2024) — 15 competencies across five aspects
  (human-centred mindset; ethics of AI; AI foundations and applications; AI pedagogy; AI for
  professional learning), in three progression levels: **Acquire, Deepen, Create**.
  <https://www.unesco.org/en/articles/ai-competency-framework-teachers>
- **UNESCO AI competency framework for students** (2024) — 12 competencies across four dimensions
  (human-centred mindset; ethics of AI; AI techniques and applications; AI system design), in three
  levels: **Understand, Apply, Create**. UNESDOC record `pf0000391105`.
  <https://www.unesco.org/en/articles/ai-competency-framework-students>

**Two things could not be verified, and are flagged rather than invented:**

1. The phrases *"AI-literate educator"* and *"AI-enhanced educator"* do not appear in either UNESCO
   framework as progression levels, and searching did not find them there. UNESCO's actual labels are
   Acquire / Deepen / Create (teachers) and Understand / Apply / Create (students). Use UNESCO's
   wording in anything carrying a UNEVOC logo. Both frameworks were released at Digital Learning Week
   2024; no post-2024 revised edition was found as of July 2026, so re-check the two article pages
   above before presenting.
2. The dates in the Part 1 timeline for loop engineering — `/goal`-style commands in early 2026, the
   term being named publicly on 7 June 2026 — come from Lecture 13 of Learn Harness Engineering and
   are attributed to it there. They are that source's account, reported as such, not independently
   corroborated here.

---

## Ground rules baked into the code

- **Offline only.** Every script talks to `http://127.0.0.1:11434` and nothing else. `report.html` is
  self-contained: the chart is an embedded base64 PNG, all CSS is inline, there is no CDN link.
- **No OCR of figures.** The ingestion step notes images by caption and stops. A number that exists
  only inside a picture does not enter the dataset, and the report says so. An unmarked guess is
  worse than an acknowledged gap.
- **Model provenance is recorded.** Every generation step logs which model produced it, and that
  provenance appears in `report.md`, the HTML footer, `state.json` and `agent_log.md`.
- **Bounded everything.** `MAX_ATTEMPTS = 3` in File D, `MAX_STEPS = 40` in the agent. Neither loop
  can run away.
- **Standard library for the harness core.** State, verification, logging and the Ollama client use
  no third-party packages. The three dependencies in `requirements.txt` are for the document work
  only, and all three run offline.

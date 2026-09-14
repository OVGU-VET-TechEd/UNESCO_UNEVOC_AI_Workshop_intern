# Part 1 — Four Levels of "Engineering" an LLM System

**Audience:** staff / facilitators (background reading). Students see the condensed version in the
cheatsheet (Part 2, File B) and slides 2–4 of the LiaScript deck (Part 2, File A).

**Purpose:** give a shared vocabulary before anyone touches a terminal. The four levels are
*cumulative*, not competing. Each one keeps everything below it and adds a layer that fixes a
failure the layer below could not fix.

---

## 1. The comparison table

| | **1. Prompt Engineering** | **2. Skill Engineering** | **3. Harness Engineering** | **4. Loop Engineering** |
|---|---|---|---|---|
| **(a) One-sentence definition** | Crafting the single instruction and context handed to one model call so that one call returns a usable answer. | Packaging reusable procedural knowledge into a file the model loads on demand, so you stop re-explaining the same conventions every session. | Designing everything *outside the model weights* — instructions, tools, environment, state, feedback — so that a fixed model executes reliably over long, multi-session tasks. | Designing the system that prompts the agent for you: propose → execute → evaluate → revise, running unattended until a machine-checkable stop condition is met — including optimising the harness itself. |
| **(b) Unit of iteration** (what you edit to improve the system) | **The prompt string.** | **The skill file** (`SKILL.md`, agent persona file, slash-command definition). | **The harness code and its artifacts**: `AGENTS.md`, tool definitions, state file, verification command, environment setup. | **The evaluation signal and the stop condition** — what counts as "better", who judges it, and when the loop is allowed to stop. |
| **(c) Failure mode it fixes relative to the level below** | (baseline) Model answers the wrong question because the request was ambiguous. | Prompt drift and re-explanation: the same conventions get typed differently every session, so output quality is inconsistent across people and days. | The "verification gap" and cross-session state loss: the model declares victory when it isn't done, and every new session re-discovers the project from scratch. Lecture 01 lists five recurring causes — vague requirements, unwritten conventions, incomplete environment, no verification method, and lost state between sessions. | Human throughput becomes the bottleneck: the harness is sound, but nothing happens unless a person presses "go" for every step. Lecture 13 frames this as moving the human from *inside* the loop to *outside* it. |
| **(d) Concrete example in this project's stack** | You paste one long prompt into `ollama run gemma3:12b` asking for a LiaScript module on hydraulic safety; the reply uses `##` where LiaScript needs `#` for slides, so you re-type the prompt with the rule added. | You write `skills/liascript-module/SKILL.md` on the DGX Spark stating the slide syntax, quiz syntax and metadata header once; every authoring session loads it, so all five BMAD agents emit the same dialect. | The course repo becomes the system of record: `AGENTS.md` names the model and the verification command, `feature_list.json` lists the modules to write, `PROGRESS.md` survives the SSH session dropping, and `liaex --format scorm1.2` is the pass/fail check before any module is marked done. | A nightly job on the DGX Spark reads `feature_list.json`, picks the highest-priority unwritten module, generates it with `gemma3:12b`, has `deepseek-r1:14b` verify it against the rubric, commits only on pass, and stops when every entry reads `passing`. |
| **(e) When it became common practice** | 2020–2022. Widespread from the GPT-3 API onward; the term is mainstream by 2022. | 2023–2025. Precursors in 2023 (system prompts, custom assistants); the file-based form (`SKILL.md` folders, BMAD-style agent files) becomes standard practice through 2025. | 2025. Named and documented as a discipline in 2025 by OpenAI ("Harness engineering: leveraging Codex in an agent-first world") and Anthropic ("Effective harnesses for long-running agents"); reaches technology-radar visibility the same year. | 2026. `/goal`-style loop commands ship in mainstream coding agents in early 2026; the term "loop engineering" is named publicly on 7 June 2026; harness *auto-optimisation* is published as Meta-Harness (COLM 2026). |

---

> **Simplicity Statement — Harness Engineering**
> A harness does not make the model smarter. It gives a fixed model a place to keep state, a way to
> check its own work, and rules for when to stop. Everything else in this package is one worked
> example of that idea.

---

## 2. Prose timeline

**2020–2022 — the prompt is the product.** With the first widely available completion APIs, the only
control surface anyone had was the text going in. Improving a system meant rewording it. This works
well for single-shot tasks and remains the correct level for most classroom use: a lecturer asking for
five exam questions does not need a harness.

**2023–2025 — knowledge gets packaged.** As people repeated the same instructions daily, the
instructions moved out of the chat window and into files. First as system prompts and custom
assistants (2023), then as versioned, on-demand-loadable skill folders — a `SKILL.md` with
instructions and metadata, optionally with scripts and reference assets alongside. Lecture 13 of the
Learn Harness Engineering course describes a skill as a way of "paying your intent debt": conventions
written down once on the outside of the model, read on every run. In this project, that is exactly what
the five BMAD agent files (`@analyst`, `@architect`, `@author`, `@qa`, `@packager`) do.

**2025 — the surrounding system gets a name.** Two things forced the issue. Benchmarks showed strong
models still failing on real, under-specified tasks, and practitioners noticed that the *same* model
succeeded or failed depending on the repository it was dropped into. Lecture 01 reports a controlled
comparison in which an identical model, given an identical prompt, produced a broken result with no
supporting structure and a working one with a planner/generator/evaluator structure around it — same
weights, different infrastructure. Lecture 02 gives the definition this package uses: a harness is
everything in the engineering infrastructure outside the model weights, decomposed into five
subsystems — **instructions, tools, environment, state, feedback** — and it warns explicitly that a
prompt file alone is *not* a harness. The Meta-Harness paper (Lee, Nair, Zhang, Lee, Khattab, Finn,
COLM 2026) gives the same object a tighter engineering definition: the harness is the code determining
what to store, retrieve, and present to an LLM. Both definitions point at the same thing from
different ends — the course from workflow, the paper from code.

**2026 — the human steps out of the loop.** Once single runs were reliable, the remaining bottleneck
was the person typing "now do the next one". Loop engineering replaces that person with a system:
a goal, a verification method, and a stop condition. Lecture 13's central reliability rule is
**generator/evaluator separation** — the agent that produced the work must not be the agent that
judges it, because a model is, in the lecture's phrase, its own output's best defence attorney. The
Meta-Harness paper closes the circle by making the *harness itself* the thing being optimised: an
agent reads a filesystem holding every prior candidate's source code, execution traces and scores,
proposes a new harness, the new harness is evaluated on held-out tasks, the logs go back into the
filesystem, and the loop repeats. On their reported text-classification benchmarks the discovered
harness reaches 48.6% against 40.9% for the hand-designed baseline, using fewer context tokens —
i.e. a better harness, not a better model.

---

## 3. Where this package sits

Parts 2 and 3 of this package are deliberately built at **level 3 with one foot in level 4**. The
worked example in Part 3 ships two variants of the same task: a *semi-agent* (level 3 — fixed
sequence, human checkpoint, no autonomous retry) and an *agent* (level 4 — the program chooses its
own next action, verifies it, and stops itself). Running both back to back is the demonstration.

---

## 4. Mapping to the UNESCO AI competency frameworks

UNESCO published two companion frameworks at Digital Learning Week 2024: the **AI competency
framework for teachers** (15 competencies across five aspects — human-centred mindset, ethics of AI,
AI foundations and applications, AI pedagogy, AI for professional learning — organised in three
progression levels: **Acquire → Deepen → Create**) and the **AI competency framework for students**
(12 competencies across four dimensions — human-centred mindset, ethics of AI, AI techniques and
applications, AI system design — in three levels: **Understand → Apply → Create**). This four-level
timeline is a direct on-ramp for that progression: prompt engineering is *Acquire* work (evaluate,
select and use an AI tool appropriately); skill and harness engineering are *Deepen* work (integrate
AI into practice and critically assess what it produces); loop engineering, and specifically the
decision about what the stop condition should be, is *Create* work (designing a new AI-supported
workflow rather than operating someone else's).

> **Accuracy note for facilitators.** The brief for this package used the phrases "AI-literate" and
> "AI-enhanced educator". Those are **not** UNESCO's terms and searching did not find them in either
> framework. UNESCO's actual progression labels are Acquire / Deepen / Create (teachers) and
> Understand / Apply / Create (students). Please use UNESCO's wording in any material that carries a
> UNEVOC logo. Neither search nor the framework pages surfaced a post-2024 revised edition as of
> July 2026; if you are presenting after that date, re-check the two UNESCO article pages linked
> below before reusing this paragraph.

---

## 5. Further reading (cited plainly, not reproduced)

- **Learn Harness Engineering** (Walking Labs), lectures 01–13, esp. Lecture 01 *Strong Models Don't
  Mean Reliable Execution*, Lecture 02 *What a Harness Actually Is*, Lecture 13 *From Manual
  Prompting to Autonomous Loops*, and the copy-ready template library (`AGENTS.md`, `init.sh`,
  `claude-progress.md`, `feature_list.json`).
  <https://walkinglabs.github.io/learn-harness-engineering/en/>
- **Meta-Harness: End-to-End Optimization of Model Harnesses** — Yoonho Lee, Roshen Nair, Qizheng
  Zhang, Kangwook Lee, Omar Khattab, Chelsea Finn. COLM 2026. Project page:
  <https://yoonholee.com/meta-harness/> · Paper: <https://arxiv.org/abs/2603.28052> · Code:
  <https://github.com/stanford-iris-lab/meta-harness>
- **UNESCO AI competency framework for teachers** (2024):
  <https://www.unesco.org/en/articles/ai-competency-framework-teachers>
- **UNESCO AI competency framework for students** (2024):
  <https://www.unesco.org/en/articles/ai-competency-framework-students>
  (UNESDOC record for the students' framework: `pf0000391105`.)

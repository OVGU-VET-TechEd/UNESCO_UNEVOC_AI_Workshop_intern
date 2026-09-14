<!--
author:   UNESCO UNEVOC Centre Magdeburg / OVGU
email:    unevoc@ovgu.de
version:  1.0.0
language: en
narrator: US English Female
comment:  From prompting to harnesses to loops — a practical introduction for lecturers,
          TVET instructors and researchers, built entirely on offline local models.
logo:     

@style
.lia-slide__content h2 { border-bottom: 2px solid #1a4f8a; padding-bottom: .2em; }
blockquote { border-left: 4px solid #c0762b; }
@end
-->

# From Prompting to Harnesses to Loops

**A working introduction for lecturers, TVET instructors and researchers**
UNESCO UNEVOC Centre Magdeburg · Otto von Guericke University Magdeburg

Everything in this session runs **fully offline** on a local Ollama model.
No cloud API calls, no data leaves the room.

--{{0}}--
Welcome. Two housekeeping points before we start. First, everything you will see today runs on a
model installed on the machine in front of you — nothing is sent to a cloud service, which is the
reason this material is usable with student data and with unpublished curriculum material. Second,
this deck is itself a file you can edit: it is plain Markdown in the LiaScript dialect, so you can
fork it for your own department. Ask people to open the runbook for their operating system now, so
the model download starts in the background while we talk.

    {{1}}
> **Who this is for**
>
> - **Sections 1–3** — everyone (students and staff).
> - **Section 4 and the facilitator notes under every slide** — staff and facilitators.

--{{1}}--
The deck carries two audiences. Sections one to three are the conceptual core and work as a student
lecture. Section four is the live demo and is written for whoever is driving the machine. Every slide
has a speaker note underneath it, which you are hearing now if narration is switched on.

## Section 1 — Why Prompting Alone Breaks Down

### The uncomfortable benchmark

    {{0}}
As of late 2025, the strongest coding agents solve roughly **50–60%** of tasks on a curated benchmark
where every task has a clear description and a ready-made test.

    {{1}}
Real work has neither. Vague requirements, unwritten conventions, no tests.
The rate goes **down**, not up.

    {{2}}
> The usual reaction: *"the model isn't good enough — let me pay for a better one."*
> That reaction is wrong more often than it is right.

--{{0}}--
Start with the number, because it sets expectations honestly. On carefully curated software tasks,
the best agents in late twenty twenty-five were somewhere in the fifty to sixty percent range. Those
tasks came with clear descriptions and ready-made tests.

--{{1}}--
Your actual work does not look like that. A course module brief is vague. Departmental conventions
live in people's heads. There is no automated test for "is this module pedagogically sound".

--{{2}}--
And here is the reflex we want to interrupt today. When the output is disappointing, almost everyone
reaches for a bigger model. Sometimes that is right. More often the model was fine and the
*environment around it* was the problem. That is the entire thesis of the session.

### Same model, different outcome

    {{0}}
Lecture 01 of *Learn Harness Engineering* reports a controlled comparison:

    {{1}}
| | Run A | Run B |
|---|---|---|
| Prompt | identical | identical |
| Model | identical | identical |
| Supporting structure | none | planner + generator + evaluator |
| Result | core features broken | working artefact |

    {{2}}
**Nothing about the model changed.** The infrastructure around it did.

--{{0}}--
This comparison is from lecture one of the Learn Harness Engineering course, which is in your
further-reading list. I am summarising it rather than quoting it.

--{{1}}--
Same prompt, same model, two runs. The only difference is that the second run had a structure around
it: something that planned, something that generated, and something separate that evaluated. The
first run produced something that did not work. The second produced something that did.

--{{2}}--
Say this line out loud to the room, because it is the sentence people should leave with: the model
did not change. Everything outside the model changed. If you remember one thing from section one,
that is it.

### The five places work actually gets stuck

    {{0}}
1. **Vague requirements** — the model has to guess, and a correct guess is luck.
2. **Unwritten conventions** — your department's rules exist in your head and one email.
3. **Incomplete environment** — the model burns its attention fixing setup, not doing the task.
4. **No verification method** — it stops when it *feels* finished.
5. **Lost state between sessions** — every new session re-discovers everything.

    {{1}}
> Notice: **not one of these five is a knowledge problem.** They are all engineering problems.

--{{0}}--
Lecture one groups real failures into five buckets. Walk through them slowly — this list is the
diagnostic tool people will actually reuse next week. Ask the room, for each one, whether they have
seen it. Usually every hand goes up on number four and number five.

--{{1}}--
This is the pivot into section two. None of these five failures is fixed by a smarter model. They are
fixed by writing things down, setting up the environment properly, defining a check, and saving state
to disk. That collection of fixes has a name.

### Section 1 quiz

A department reports that their local model "used to write good module descriptions and now writes
bad ones", although the model file has not been changed. Which failure bucket should you check
**first**?

    [( )] The model has degraded and needs re-downloading.
    [(X)] Unwritten conventions — different people are prompting it differently.
    [( )] The model is too small for the task.
    [( )] Nothing can be done; output quality is inherently random.
***********************************************

Nothing about a local model file changes on disk between runs. When output quality varies while the
model is fixed, the variable is what is being sent *in* — which is a conventions-and-instructions
problem, and it is exactly what a skill file or an `AGENTS.md` is for.

***********************************************

--{{0}}--
Give the room thirty seconds. The distractor people pick most often is "the model is too small",
which is a good teaching moment: it is the same reflex as buying a bigger model.

## Section 2 — What a Harness Actually Is

### Definition

    {{0}}
> A **harness** is everything in the engineering infrastructure **outside the model weights**.
> If it is not model weights, it is harness.
> — paraphrased from Lecture 02, *Learn Harness Engineering*

    {{1}}
> The **Meta-Harness** paper (Lee et al., COLM 2026) defines the same object from the code side:
> the harness is the code determining **what to store, retrieve, and present** to an LLM.

    {{2}}
**A prompt file on its own is not a harness.** That is the most common misuse of the word.

--{{0}}--
Two definitions, deliberately. The course definition is behavioural and easy to remember: if it is
not model weights, it is harness.

--{{1}}--
The paper's definition is the one engineers in the room will prefer, because it names the three verbs
that matter: store, retrieve, present. Attribute it properly — Lee, Nair, Zhang, Lee, Khattab and
Finn, presented at COLM twenty twenty-six.

--{{2}}--
And the correction that saves the most confusion later: many people say "harness" when they mean
"my prompt file". A prompt file is one of five components, and not the most valuable one.

### The five subsystems

    {{0}}
| Subsystem | What it is | Concretely, in a repo |
|---|---|---|
| **Instructions** | The operating rules | `AGENTS.md` — a map, ~100 lines, not an encyclopaedia |
| **Tools** | What the agent may do | shell, file read/write, the export command |
| **Environment** | Reproducible setup | `requirements.txt`, pinned model tag, `init.sh` |
| **State** | Memory that outlives a session | `PROGRESS.md`, `feature_list.json`, a JSON state file |
| **Feedback** | How it knows it is right | one verification **command** with a pass/fail exit |

    {{1}}
> **Feedback is the cheapest subsystem to add and the one with the biggest return.**
> Get your verification command right before you touch anything else.

--{{0}}--
This table is the spine of the whole session. Everything in the demo later maps onto exactly one of
these five rows, and I will say which row each time. Encourage people to photograph this slide.

--{{1}}--
If your audience only implements one row, make it feedback. Lecture two is explicit that this is the
lowest-investment, highest-return subsystem. A single command that returns pass or fail turns "the
model says it is done" into "the system confirms it is done".

### The repository is the system of record

    {{0}}
**Anything the agent cannot see does not exist.**

    {{1}}
The minimal file set, from the course's copy-ready template library:

```text
AGENTS.md          the operating rules — read first, every session
feature_list.json  the work items, with status and verification steps
PROGRESS.md        what is done, in progress, blocked — written at session end
init.sh            install, verify, report — one command, reproducible
```

    {{2}}
Status values in `feature_list.json`: `not_started` · `in_progress` · `blocked` · `passing`
**Only one item may be `in_progress` at a time.** That single rule prevents most scope sprawl.

--{{0}}--
The phrase "the repository is the system of record" is doing a lot of work here. It means the folder
on disk — not the chat history, not your memory — holds the truth about the project.

--{{1}}--
Four files. That is the whole minimum harness. They are on the cheatsheet in your handout as blank
skeletons you can fill in. This is genuinely all it takes to move a project from unreliable to
reliable.

--{{2}}--
Point at the one-item-in-progress rule specifically. In teaching contexts this is the rule people
find surprising and then adopt permanently, because it applies to human project work too.

### Why verification cannot be self-assessment

    {{0}}
Agents **declare victory early**. Consistently. Not dishonestly — structurally.

    {{1}}
> A model is its own output's best defence attorney.
> — paraphrasing Lecture 13

    {{2}}
So the check must be **outside** the thing being checked:

- a command with an exit code (`pytest`, `liaex --format scorm1.2`), **or**
- a *different* model with different instructions doing the judging.

    {{3}}
This is called **generator/evaluator separation**, and it is the single most important reliability
rule in this whole session.

--{{0}}--
The gap between how confident an agent sounds and whether it is actually correct has a name — the
verification gap — and it is the most common failure mode reported in lecture one.

--{{1}}--
The reason is not that the model is lying. It is that the model convinced itself the path was right
while generating. Looking back, it sees its own reasoning, not its mistakes.

--{{2}}--
Two acceptable checks. A command that exits zero or non-zero is the strongest, because it cannot be
argued with. A second model with different instructions is the fallback when the thing being checked
is prose rather than code.

--{{3}}--
Name the rule explicitly and write it on the whiteboard if you have one. The demo in section four
implements exactly this: a rule-based check that the generator never sees.

### Section 2 quiz

Which of the following belong to the **harness**? (Select all that apply.)

    [[X]] A `PROGRESS.md` file updated at the end of every session
    [[ ]] The number of parameters in `gemma3:12b`
    [[X]] The command `liaex --format scorm1.2` used to check an export succeeds
    [[X]] A JSON file listing which modules still need writing
    [[ ]] The training data the model was built from
***********************************************

Harness = everything outside the model weights. Parameter count and training data are the weights.
State files, work lists and verification commands are all harness — and the verification command is
the highest-value item on the list.

***********************************************

--{{0}}--
The two distractors are deliberately the two things people most often try to fix first. If someone
selects them, that is a productive conversation rather than a wrong answer.

## Section 3 — Harness vs. Loop

### Who presses "start"?

    {{0}}
| | **Harness** (Level 3) | **Loop** (Level 4) |
|---|---|---|
| You provide | the next instruction | the goal and the stop condition |
| The agent | executes once | repeats until the condition is met |
| Who judges "done" | you | an independent evaluator |
| You can walk away | no | yes |

    {{1}}
> **A loop needs exactly three things: a goal, a verification method, and a stop condition.**

    {{2}}
Loop engineering does not replace harness engineering. It is built **one floor above** it.
A loop without a working harness just fails repeatedly, faster.

--{{0}}--
This table is the cleanest way to draw the boundary. Note the last row: the practical test for
whether you have a loop is whether you can close the laptop.

--{{1}}--
Three things. Goal, verification, stop condition. If someone asks "how do I make my agent
autonomous", this is the answer, and it is short enough to remember.

--{{2}}--
Emphasise this, because it is where enthusiasm causes damage. Automating an unverified process just
produces broken output at scale. Harness first, then loop.

### The Meta-Harness search loop

    {{0}}
The Meta-Harness paper applies the loop to the harness **itself**. Four steps, repeating:

```text
        ┌──────────────────────────────────────────────┐
        │                                              │
        ▼                                              │
  (1) PROPOSE ──▶ (2) EVALUATE ──▶ (3) LOG ────────────┘
   an agent reads    run the new      write source, traces
   a filesystem of   harness on       and scores back into
   every prior       held-out tasks   the filesystem
   candidate's
   code, traces
   and scores
```

    {{1}}
The design choice that matters: the proposer gets the **raw execution traces**, not a summary score.
It can read the logs with ordinary tools and trace a failure back to the specific harness decision
that caused it.

    {{2}}
Reported result on text classification: **48.6%** for the discovered harness vs **40.9%** for the
hand-designed baseline — with fewer context tokens. *Better harness, same model.*

--{{0}}--
Describe the diagram rather than reading it. An agent proposes a new harness; the new harness is
evaluated on tasks it has not seen; everything — code, traces, scores — is written back to a
filesystem; the loop repeats using that accumulated evidence.

--{{1}}--
This is the part worth dwelling on for a research audience. Most optimisation methods compress
history into a score or a short summary. Meta-Harness keeps the full logs and lets the proposer read
them. That is why it can diagnose rather than guess.

--{{2}}--
Give the numbers, then give the interpretation. The interpretation is the reusable lesson: the
improvement came from changing the code around the model, not from changing the model.

### The four costs of running loops

    {{0}}
1. **Verification debt** — "looks fine" quietly replaces "confirmed correct".
2. **Comprehension rot** — output arrives faster than anyone reads it.
3. **Cognitive surrender** — the loop is used to avoid thinking rather than to amplify it.
4. **Token blowout** — context grows every iteration unless it is actively managed.

    {{1}}
> Two people can build the same loop and get opposite results: one goes faster on work they
> understand, the other avoids understanding the work. *The loop cannot tell the difference.*
> — paraphrasing Osmani, via Lecture 13

--{{0}}--
Do not skip this slide even when you are short of time. For an education audience it is the most
transferable content in the session, because items two and three are exactly the concerns raised
about students using generative AI — stated here as engineering risks rather than as a moral panic.

--{{1}}--
This is also the natural hook into the UNESCO framework mapping: critical evaluation of AI output is
not an add-on ethics module, it is the mechanism that keeps the system working.

### Section 3 quiz

Your loop runs overnight and generates twelve course modules. In the morning all twelve are marked
`passing`. What is the **first** thing to check?

    [( )] Whether the model needs upgrading to produce better prose.
    [( )] Whether the loop ran fast enough.
    [(X)] Who or what marked them `passing`, and whether that judge was independent of the generator.
    [( )] Whether twelve was the right number of modules.
***********************************************

If the agent that wrote the modules also decided they passed, the `passing` label carries no
information. Generator/evaluator separation is what makes an overnight run trustworthy — a command
with an exit code, or a different model with different instructions.

***********************************************

--{{0}}--
This is the applied question in the middle of the deck; the final applied question is in the closing
quiz. If people answer this one correctly, section three has landed.

## Section 4 — Live Demo (facilitators)

### What you are about to run

> **Staff / facilitator section.** Students watch; you drive.

    {{0}}
Two programs. **Same task, same model, same machine.** Only the control flow differs.

    {{1}}
| | **A — Semi-agent** | **B — Agent** |
|---|---|---|
| Order of steps | fixed, written by us | chosen by the program each turn |
| Human checkpoint | yes, before the report | no |
| On failure | stops, you look | verifies, retries, logs why |
| Stops because | the script ended | every PDF appears in the report |
| Artefact to read afterwards | the intermediate files | `agent_log.md` |

    {{2}}
Both convert **PDF → Markdown** first. That is not decoration: clean Markdown is what makes
downstream chunking and retrieval work at all.

--{{0}}--
Frame the demo before you start it, because the interesting part is not the output — it is the
difference in control flow. The output of both programs is roughly the same report.

--{{1}}--
Walk the table left to right. The right-hand column is the one that needs the stop condition, and
that is the whole point.

--{{2}}--
Mention the ingestion step explicitly. People with a research background will immediately see why:
PDF text extraction quality sets a ceiling on everything downstream.

### Run it

    {{0}}
```bash
cd part3_worked_example
python semi_agent.py --model llama3.1:8b     # stops at the human checkpoint
python agent.py       --model qwen2.5:7b     # runs to its own stop condition
```

    {{1}}
Then open, in this order:

```text
output_semi/report.md          the written report
output_semi/report.html        the table + chart
output_agent/agent_log.md      ← the teaching artefact
```

    {{2}}
> **Read `agent_log.md` aloud.** It is a plain-language record of every decision the agent made and
> why. It is the most convincing five minutes of the session.

--{{0}}--
Run both live if the room's machine allows it. If time is short, run the semi-agent live and open a
pre-generated agent log. Note the model flag: the two programs are running different local models,
and each generation step records which model produced it.

--{{1}}--
Open the files in this order deliberately. Report first so people see the outcome, log last so the
mechanism is the thing they leave with.

--{{2}}--
The log is written in ordinary sentences on purpose — "I checked whether X existed, it did not, so I
did Y." Non-programmers can follow it, and it makes the state / verification / stop-condition
structure visible without reading any Python.

### Which lines are the harness?

    {{0}}
In `agent.py`, roughly **fifteen lines** send text to the model.
Everything else — several hundred lines — is harness.

    {{1}}
| In the code | Subsystem |
|---|---|
| `state.json` read/write | **State** |
| `verify_output()` — file exists and is non-empty | **Feedback** |
| `all_pdfs_covered()` — the stop condition | **Feedback** |
| `agent_log.md` append | **Feedback / observability** |
| `TOOLS = {...}` — the five permitted actions | **Tools** |
| `call_ollama()` | ← *this is the model call, not the harness* |

    {{2}}
> **Simplicity Statement — Harness Engineering**
> A harness does not make the model smarter. It gives a fixed model a place to keep state, a way to
> check its own work, and rules for when to stop. Everything else in this package is one worked
> example of that idea.

--{{0}}--
Open the file and scroll. The visual impression of scrolling past hundreds of lines of harness to
find fifteen lines of prompt is worth more than any slide.

--{{1}}--
Go row by row with the file open on screen. This table is the single most important pedagogical
moment in the package.

--{{2}}--
Close on the simplicity statement. It is printed on the cheatsheet too, so people take it home.

## Closing Quiz

### Five questions

**1.** A harness is best defined as:

    [( )] A well-written prompt template.
    [(X)] Everything in the engineering infrastructure outside the model weights.
    [( )] The graphics card the model runs on.
    [( )] A fine-tuned version of a base model.

**2.** Which subsystem is described as the cheapest to add with the highest return?

    [( )] Instructions
    [( )] Tools
    [(X)] Feedback (verification)
    [( )] Environment

**3.** A loop requires exactly three things. Select them.

    [[X]] A goal
    [[X]] A verification method
    [[X]] A stop condition
    [[ ]] A larger model
    [[ ]] An internet connection

**4.** Why must the agent that produced the work not be the agent that judges it?

    [( )] Because it would take twice as long.
    [(X)] Because a generator systematically over-rates its own output — it sees its reasoning, not its mistakes.
    [( )] Because local models cannot self-evaluate at all.
    [( )] Because judging requires a larger context window.

**5. Applied.** Your institute wants to auto-generate one microcredential module per week from a
syllabus folder, unattended, on an offline server. You have a working prompt and a model. Which
**single** addition most reduces the risk of publishing a broken module?

    [( )] Switch to a larger model.
    [( )] Write a longer, more detailed prompt.
    [(X)] Add a machine-checkable verification command (e.g. the SCORM export must succeed) that must pass before a module is marked done.
    [( )] Run the generation three times and keep the longest output.
***********************************************

Question five is the whole session in one decision. A larger model, a longer prompt and
best-of-three all act on the generator. Only the verification command changes what the system is
allowed to call "finished" — and that is what stops broken output from reaching a learner.

***********************************************

--{{0}}--
Questions one to four are recall; question five is the applied one. If you are running a shortened
session, ask only question five — it carries the argument on its own. Answers can be discussed in
plenary; the built-in solutions appear when learners submit.

## Further Reading & Framework Alignment

### Sources used in this deck

    {{0}}
- **Learn Harness Engineering** (Walking Labs) — lectures 01, 02 and 13 in particular, plus the
  copy-ready template library (`AGENTS.md`, `init.sh`, `claude-progress.md`, `feature_list.json`).
  <https://walkinglabs.github.io/learn-harness-engineering/en/>
- **Meta-Harness: End-to-End Optimization of Model Harnesses** — Lee, Nair, Zhang, Lee, Khattab,
  Finn. COLM 2026. <https://yoonholee.com/meta-harness/> · <https://arxiv.org/abs/2603.28052>
- **UNESCO AI competency framework for teachers** (2024) —
  <https://www.unesco.org/en/articles/ai-competency-framework-teachers>
- **UNESCO AI competency framework for students** (2024) —
  <https://www.unesco.org/en/articles/ai-competency-framework-students>

    {{1}}
> **UNESCO alignment for this deck.** Sections 1–2 support the teachers' framework aspect
> *AI foundations and applications* at the **Acquire** level: understanding what an AI system is
> composed of well enough to evaluate and select tools rather than accept them. Section 3 sits at
> **Deepen** — critically assessing AI-supported workflows and their risks, with the four costs of
> looping mapping onto the framework's human-agency and accountability principles. Section 4 is
> **Create**-level work: designing a verification rule for your own institutional context. For
> students, the same material maps to *AI system design* at **Understand → Apply**. UNESCO's
> progression labels are Acquire / Deepen / Create for teachers and Understand / Apply / Create for
> students; other level names sometimes attributed to these frameworks are not UNESCO's wording.

--{{0}}--
Leave this slide up during questions. Everything asserted in the deck comes from one of these four
sources, and all four are freely accessible.

--{{1}}--
One note if you are adapting this deck: quiz syntax in LiaScript is single choice with round
brackets, `[( )]` and `[(X)]`, and multiple choice with square brackets, `[[ ]]` and `[[X]]`. Some
summaries of LiaScript state this the other way round. What is in this file is the working syntax —
render it at liascript.github.io to confirm before you edit.

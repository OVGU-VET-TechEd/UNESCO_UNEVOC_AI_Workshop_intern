# Part 4 — The UNESCO brief, covered

*Draft material responding directly to the three areas UNESCO named: what AI assistants, agents and
knowledge bases are and how they work; UNEVOC use cases; and a practical demonstration built on
public or anonymised documents.*

---

## Coverage of the brief

| UNESCO asked for | Delivered here |
|---|---|
| **AI assistants, agents and knowledge bases — what they are and how they work, explained in practical terms** | `A_definitions_assistants_agents_knowledge_bases.md` — eleven terms defined precisely, a commonly-confused-pairs table, and a "which one do you need" decision table with effort estimates |
| **UNEVOC use cases: document review, knowledge management, project monitoring, training development** | `B_unevoc_use_cases.md` — all four, each to the same eight headings, each with a pilot specification including a stated failure criterion |
| **Practical demonstration: build or test a simple assistant using public or anonymised documents** | `demo_assistant/` — a working, offline, cited-and-refusing document assistant, plus an anonymisation pass and an evaluation harness. Tested end to end |
| *(implied)* something to present from | `D_liascript_deck_assistants.md` — four sections, quizzes, facilitator notes under every slide |
| *(implied)* something to decide with | `C_pilot_selection_worksheet.md` — a ten-question scoring worksheet, plus five questions to ask any vendor |

---

## Files

```text
part4_unesco_brief/
├── 00_PART4_INDEX.md                                    ← you are here
├── A_definitions_assistants_agents_knowledge_bases.md   the definitions
├── B_unevoc_use_cases.md                                the four use cases
├── C_pilot_selection_worksheet.md                       scoring worksheet, print one per candidate
├── D_liascript_deck_assistants.md                       the deck
└── demo_assistant/
    ├── README.md              ← read before running anything
    ├── make_corpus.py         eight synthetic documents (replace with your own)
    ├── anonymise.py           scrub direct identifiers; writes a report a human must read
    ├── kb_build.py            documents → passages → kb.json
    ├── ask.py                 retrieve → ground → verify → answer with citations, or refuse
    ├── eval_kb.py             run a fixed question set, report three numbers
    ├── eval_questions.json    twelve questions, three of which must be refused
    ├── requirements.txt
    ├── corpus_raw/            the documents as given
    ├── corpus/                after anonymisation — this is what gets indexed
    ├── kb.json                the knowledge base (plain text; open it)
    └── anonymisation_report.md every replacement made, for human review
```

`corpus/`, `kb.json` and `anonymisation_report.md` are shipped pre-built so a facilitator can open
and read them before running anything. Re-running the scripts regenerates them.

---

## The three sentences this part exists to establish

1. **Everything you care about lives outside the model.** Memory, knowledge of your documents,
   the ability to act — all of it is software around a fixed function that predicts text.
2. **A knowledge base is a searchable folder with labels.** Nothing was trained; passages are copied
   into the prompt at question time; you can update or delete in seconds.
3. **A system without a defined refusal is not deployable.** What does it do when it cannot do the
   job? If the answer is "produce something anyway", the answer is no.

---

## Session plan — 2 hours

Run the demo once yourself beforehand, following `demo_assistant/README.md`.

| # | Minutes | Do this | File |
|---|---|---|---|
| 1 | 0–10 | Frame the session. Everything runs locally; nothing leaves the room. | deck title slide |
| 2 | 10–30 | Section 1: what a model is and is not. The context window as a budget. | deck §1 |
| 3 | 30–50 | Section 2: knowledge bases and RAG. **Open `kb.json` on screen and scroll it.** | deck §2 + `kb.json` |
| 4 | 50–65 | Section 3: assistants vs agents; how tools actually work. | deck §3 |
| 5 | 65–85 | **Live demo.** Ask a covered question. Then ask the Peru question. Then open `ask_log.md` and show which of the three defences fired. | `demo_assistant/` |
| 6 | 85–95 | Run `eval_kb.py`. Three numbers. Then set `MIN_TERM_COVERAGE = 0.0`, re-run, and watch the refusal rate collapse. | `eval_kb.py` |
| 7 | 95–110 | The four use cases. Name them, do not lecture them. Hand out file B. | deck §4 + file B |
| 8 | 110–120 | Closing quiz (question 5 alone if short). Then work through the scoring worksheet for **one** candidate use case, in plenary. | deck quiz + file C |

**If you have 45 minutes:** steps 2, 3, 5, and closing question 5.

**Follow-up task to set:** each participant collects five real questions from their own work that
they would want a knowledge assistant to answer, plus two it should refuse. Those seven questions per
person become the evaluation set for a pilot. This is the single most useful preparatory activity,
and it costs nobody any technical effort.

---

## Relationship to Parts 1–3

Part 4 is self-contained and can be delivered on its own. It sits on the same foundation:

- **Part 1** — the four levels of engineering an LLM system (prompt → skill → harness → loop).
- **Part 2** — harness engineering taught in depth, plus the runbooks that install Ollama and two
  models. Use those runbooks for Part 4 too; the setup is identical.
- **Part 3** — semi-agent vs agent on a document-processing task. The natural follow-on session for
  anyone who chooses project monitoring or training development as a pilot.

> **Simplicity Statement — Harness Engineering**
> A harness does not make the model smarter. It gives a fixed model a place to keep state, a way to
> check its own work, and rules for when to stop. Everything else in this package is one worked
> example of that idea.

---

## Status and caveats

This is **draft material for internal review**, not a published UNESCO product.

- The demo corpus is **synthetic**, written for this package. It is not UNESCO or UNEVOC material and
  contains no real policy, project data or people.
- Effort and duration estimates in file B are professional judgement, offered as planning anchors.
  They are not derived from a survey.
- The retrieval thresholds in `ask.py` are tuned to the demo corpus and **will be wrong for yours**.
  `eval_kb.py` exists to re-tune them; this is documented in the demo README.
- UNESCO framework references throughout use the 2024 editions and UNESCO's own progression labels
  (Acquire / Deepen / Create for teachers; Understand / Apply / Create for students). No post-2024
  revised edition was found when this material was prepared; re-check before external use.

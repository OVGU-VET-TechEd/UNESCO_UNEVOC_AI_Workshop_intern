# B — Four UNESCO-UNEVOC use cases

*Draft teaching material. Each use case is written to the same eight headings so they can be compared
side by side and one can be chosen as a pilot. The pattern names — assistant, semi-agent, agent — are
defined precisely in File A.*

---

## Summary comparison

| | 1. Document review | 2. Knowledge management | 3. Project monitoring | 4. Training development |
|---|---|---|---|---|
| **Pattern** | Assistant (+ checklist) | Assistant + knowledge base | Semi-agent | Semi-agent → agent |
| **Human role** | Reviewer of every output | Asker; spot-checks citations | Confirms before anything is circulated | Author and approver |
| **Knowledge base?** | The document under review only | Yes — this *is* the use case | Reporting templates + prior reports | Curriculum standards + house style |
| **Hardest part** | Deciding what "review" means | Document preparation, not AI | Distinguishing variance from noise | Assessment design |
| **Main risk** | Fluent approval of weak work | Confident answer from an outdated document | A trend asserted from four data points | Plausible content misaligned to outcomes |
| **Time to pilot** | 2–3 weeks | 4–6 weeks | 6–8 weeks | 8–12 weeks |
| **Recommended order** | **Start here** | Second | Third | Fourth |
| **Verification available** | Checklist coverage (machine-checkable) | Citation check + refusal rate | Figures must match the source table | Structural rules + export succeeds |

**Recommended sequence:** document review first. It has the tightest feedback loop, the smallest
corpus, and the clearest definition of done — and it is where staff will most quickly form an
accurate intuition about what the technology can and cannot do.

---

## Use case 1 — Document review

### 1.1 The job as it is done today

A staff member reads a submitted document — a centre self-assessment, a project deliverable, a draft
module — against a set of expectations, and produces comments. The expectations are partly written
down and partly held in the reviewer's head. Reviews vary between reviewers and between Mondays and
Fridays.

### 1.2 What the technology can actually do

Not "review the document". Precisely these three things:

1. **Coverage checking.** For each item on an explicit checklist, find the passage that addresses it,
   or report that none does. This is genuinely useful and genuinely reliable, because the answer is
   located in the document rather than generated.
2. **Consistency checking.** Flag statements that appear to conflict with each other or with a named
   reference document — a stated duration in one section against a different one in a table.
3. **Drafting comments.** Turn a finding into a sentence a reviewer can accept, edit or discard.

### 1.3 What it must not do

- Issue a rating, grade or recommendation. Coverage is not quality: a section can address every
  checklist item and still be poor.
- Review anything whose checklist has not been written down first. If the criteria are not explicit,
  the output is the model's guess at your criteria.
- Be the only reviewer.

### 1.4 Pattern and knowledge base

**Assistant**, one document at a time, with the checklist supplied in the prompt. No corpus-wide
knowledge base is needed; the document under review is the corpus. This is why it is the cheapest
starting point.

### 1.5 Harness requirements

| Subsystem | Concretely |
|---|---|
| Instructions | The checklist as a file, versioned. This artefact outlives the AI project. |
| State | One findings file per document, so a review can be resumed. |
| Feedback | Every finding must quote the passage it refers to, and the quote must be verifiably present in the document — a string match, checkable by code. |
| Tools | Read the document. Nothing else. No write access. |
| Stop | Every checklist item has a status: addressed, not addressed, unclear. |

### 1.6 Verification

Machine-checkable: (a) every checklist item has a status; (b) every finding quotes text that actually
occurs in the source. Both are string operations. A finding that quotes text not present in the
document is rejected before a human sees it.

Not machine-checkable, therefore human: whether "addressed" was the right call.

### 1.7 Main risk, stated plainly

**Fluent approval.** A well-written summary of a weak document reads like a well-written document.
The mitigation is structural: the assistant reports *coverage*, never *quality*, and the reviewer's
form has no field the assistant can fill in.

### 1.8 Pilot specification

- **Corpus:** 15 already-reviewed documents for which human comments exist.
- **Duration:** three weeks.
- **Success criterion:** on ≥80% of checklist items, the assistant's coverage judgement agrees with
  the human reviewer's, and it produces **zero** quoted passages that do not occur in the source.
- **Failure criterion to accept honestly:** if writing the checklist takes longer than the reviews it
  saves, stop. That is a real and common outcome, and the checklist is still worth having.

---

## Use case 2 — Knowledge management

### 2.1 The job as it is done today

Staff need to find what an institution already knows: which centre used which quality instrument,
what was decided about stacking rules, which project already produced a green-skills module. The
knowledge exists, distributed across documents, in inconsistent formats, with no shared index. People
ask colleagues, and the answer depends on who is available.

### 2.2 What the technology can actually do

Answer natural-language questions over a prepared corpus, **with a citation for every claim and an
explicit refusal when the corpus does not cover the question**. That combination — citation plus
refusal — is what separates a usable institutional tool from a plausible-sounding one.

Also useful, and often underrated: it makes the *state of the corpus* visible. A pilot typically
reveals that key decisions were never written down anywhere. That finding is worth the pilot on its
own.

### 2.3 What it must not do

- Answer without a citation. An uncited answer must be treated as no answer.
- Serve documents to people not entitled to see them. Retrieval has no concept of permission unless
  you build one; the safe default is one knowledge base per audience.
- Be trusted on currency. If a superseded policy is in the corpus, it will be quoted as confidently
  as the current one. Corpus hygiene is the ongoing cost of this use case, and it does not go away.

### 2.4 Pattern and knowledge base

**Assistant + knowledge base (RAG).** This use case *is* the knowledge base. Budget accordingly: in
practice 70–80% of the effort is document selection, conversion, de-duplication and deciding what is
authoritative. The retrieval and the model are the easy part.

### 2.5 Harness requirements

| Subsystem | Concretely |
|---|---|
| Environment | A documented pipeline: raw → cleared/anonymised → indexed. Three folders, so "has this been cleared?" is answered by a path. |
| State | The knowledge base is a build artefact with a date and a document list, rebuilt on a schedule, never edited in place. |
| Feedback | Retrieval gate (refuse when nothing relevant is found), citation check (every marker must resolve), and a standing question set run after every rebuild. |
| Tools | Read the index. No write access, ever. |
| Stop | Answer with citations, or refuse. There is no third outcome. |

### 2.6 Verification

The demo in `demo_assistant/` implements exactly this and reports three separate numbers:

- **retrieval hit rate** — did the right document reach the prompt? If this is low, no model fixes it.
- **answered-when-expected** — questions the corpus covers get answered.
- **refused-when-expected** — questions it does not cover are declined, not invented.

Report all three separately. A single blended "accuracy" figure hides which one broke, and the
refusal number is the one that vendors do not publish.

### 2.7 Main risk

**Confident currency errors.** The system cannot tell a superseded document from a current one unless
the metadata says so. Mitigations: date every passage; exclude superseded material at build time
rather than hoping retrieval ranks it lower; show the source document's date in every answer.

### 2.8 Pilot specification

- **Corpus:** 30–80 documents that are already public, or internal documents with a named owner who
  has approved their use.
- **Duration:** 4–6 weeks, of which at least half is document work.
- **Question set:** 30–50 real questions collected from staff *before* anything is built, including
  at least eight the corpus definitely does not cover.
- **Success criterion:** ≥85% retrieval hit rate, ≥90% correct refusal on the out-of-corpus
  questions, and every answer traceable to a passage a human can open.
- **Ongoing cost to state up front:** someone owns the corpus. If nobody is named, do not start.

---

## Use case 3 — Project monitoring

### 3.1 The job as it is done today

Partners submit periodic reports in inconsistent formats. Someone extracts the figures, compares them
against planned values, identifies variance, drafts a consolidated summary, and chases what is
missing. It is repetitive, deadline-bound, and the tedium is precisely what causes errors.

### 3.2 What the technology can actually do

1. **Normalise** heterogeneous reports into one structure — converting each to Markdown first, so
   tables survive as tables.
2. **Extract** planned-versus-actual figures into a dataset that can be checked against the source.
3. **Flag** variance against thresholds *you* set. Not judge it — flag it.
4. **Draft** the narrative sections that describe what the figures show.
5. **Report what is missing**, which is often the most valuable output and requires no intelligence
   at all.

`semi_agent.py` and `agent.py` in Part 3 of this package are a working implementation of steps 1, 2
and 4 over a folder of PDFs.

### 3.3 What it must not do

- **Produce any figure that is not traceable to a source table.** Every number in the consolidated
  output must be checkable against a cell in an input document. A number the model wrote is not a
  number.
- Explain variance. It can report that a milestone slipped; it cannot know why, and a plausible
  invented cause is worse than an empty field.
- Assert a trend. Four quarters is not a trend, and the model will happily call it one.

### 3.4 Pattern and knowledge base

**Semi-agent.** The steps do not vary between reporting rounds, so there is nothing for an agent to
decide, and the human checkpoint before circulation is a genuine control rather than a formality.
Knowledge base: the reporting template, the plan of record, and prior periods for comparison.

### 3.5 Harness requirements

| Subsystem | Concretely |
|---|---|
| Instructions | The reporting template and the variance thresholds, as files. |
| State | One JSON dataset per reporting round, with the source document and page for every figure. |
| Feedback | Every extracted figure re-checked against the source text by string match. Mismatch → the field is flagged, not filled. |
| Tools | Read submissions; write drafts to a drafts folder. No access to the system of record. |
| Stop | Every partner has either a complete dataset entry or an explicit "missing" flag. |

### 3.6 Verification

Strong, and unusually so for this kind of work: extracted figures must match the source exactly. This
is a string comparison, and it catches the failure mode that actually matters. Anything the check
cannot confirm is left blank and listed as requiring manual entry.

### 3.7 Main risk

**A narrative that outruns the data.** The drafting step produces fluent prose regardless of whether
four data points support the claim. Mitigation: the drafting prompt is restricted to describing the
dataset, and the evaluation methodology note (the corpus should contain one) governs what may be
claimed. This is a governance control, not a technical one.

### 3.8 Pilot specification

- **Corpus:** one completed reporting round, already consolidated by hand.
- **Duration:** 6–8 weeks.
- **Success criterion:** ≥95% of figures extracted and verified against the source, with the
  remainder correctly flagged as unverifiable rather than silently guessed; consolidated draft ready
  for human editing in under one working day.
- **Comparison to run:** hours spent this round versus the manual round, honestly measured, including
  the time spent checking the machine's output.

---

## Use case 4 — Training development

### 4.1 The job as it is done today

Instructors and curriculum staff produce modules: learning outcomes, content, activities, assessment,
and a package for the learning management system. It is skilled work, and the routine parts —
formatting, packaging, converting between formats, writing first-draft outcome statements — consume a
disproportionate share of it.

### 4.2 What the technology can actually do

1. **Draft** learning outcomes from a topic and level, which a human then rewrites. First drafts are
   cheap; the value is in having something to react to.
2. **Restructure** existing material into a required module template.
3. **Generate** the routine scaffolding: glossaries, recap questions, worked examples.
4. **Package** — convert an authored module into the target format and export it. This step is
   deterministic and is the easiest large win.
5. **Check** a draft module against structural rules: does every outcome have an assessment, is every
   outcome observable, is the notional-hours statement present.

Item 5 is the most valuable and the least discussed, because it is verification rather than
generation.

### 4.3 What it must not do

- Design assessment. Aligning assessment to outcome is the professional judgement in this work, and a
  plausible-looking assessment that tests recall where the outcome asks for application is a real,
  frequent and damaging failure.
- Generate subject content that no human verifies. In TVET this includes safety-critical procedure,
  where fluent plausible instructions are dangerous rather than merely wrong.
- Be presented to learners as authored by a person when it was not.

### 4.4 Pattern and knowledge base

**Semi-agent first, agent later.** Start with fixed steps and an author at every checkpoint. Move to
an agent only for the packaging and checking loop, where the stop condition is genuinely
machine-checkable — the export succeeds and the structural checks pass.

Knowledge base: the curriculum standard, the module template, the house style guide, and existing
approved modules as exemplars.

### 4.5 Harness requirements

| Subsystem | Concretely |
|---|---|
| Instructions | Module template and style guide as skill files, loaded on demand. |
| State | One folder per module with a status file; only one module in progress at a time. |
| Feedback | Structural checker (outcomes observable, assessment present, hours stated) **plus** the export command exiting zero. Both must pass. |
| Tools | Read the standard; write only into the drafts folder. |
| Stop | Structural checks pass, export succeeds, and a named human has approved. The human approval is part of the stop condition, not an afterthought. |

### 4.6 Verification

Two layers, both machine-checkable: the structural checker (File D in Part 2 is a minimal working
example — it enforces action verbs, length and single-sentence form on learning outcomes), and the
export step, which fails loudly on malformed input.

Not machine-checkable, therefore human: pedagogical soundness, factual accuracy of subject content,
and safety-criticality.

### 4.7 Main risk

**Plausible content misaligned to outcomes.** The output looks like a module and reads like a module.
Structural checks confirm it *is* shaped like a module. Neither tells you it teaches the right thing.
The only mitigation is a named approver who is accountable for the content, and that person's name
should be in the module metadata.

### 4.8 Pilot specification

- **Corpus:** three modules already developed and approved, to be re-developed with support.
- **Duration:** 8–12 weeks.
- **Success criterion:** time from brief to review-ready draft reduced by ≥40%, with no increase in
  review findings per module. The second half of that sentence is the one that matters — a faster
  process producing more review work is not a saving.
- **Explicit non-goal:** removing the author. The target is removing the formatting and packaging
  work, and giving the author a draft to argue with.

---

## Cross-cutting: five things true of all four

1. **The corpus is the project.** In every case above, document preparation dominates the effort.
   Institutions that budget for "an AI project" and not for "a document project" run out of time in
   the same place.
2. **Every use case needs a defined refusal.** What does the system do when it cannot do the job? If
   the answer is "produce something anyway", it is not deployable.
3. **Verification is what distinguishes these from a demo.** Checklist coverage, citation resolution,
   figure matching, structural checks — each is ordinary, boring code, and each is what makes the
   output auditable.
4. **Name an owner before starting.** For the corpus, and for the output. An assistant with no owner
   becomes a stale assistant within two quarters, and a stale assistant is worse than none because
   people still trust it.
5. **Measure against the manual baseline, honestly.** Including the time spent checking the machine.
   Several of these use cases will pay back clearly; at least one, in any given institution, will
   not, and finding out which is the point of a pilot.

---

## UNESCO framework alignment

This file supports the *Deepen* level of the **UNESCO AI competency framework for teachers** (2024)
under the aspects *AI pedagogy* and *AI for professional learning*: integrating AI into professional
practice while critically assessing its effects, rather than adopting it wholesale. The "what it must
not do" and "main risk" headings in each use case operationalise the framework's human-centred
mindset and accountability principles — in each case a named human remains accountable for the
decision, and the system is constrained so that it cannot quietly take that decision instead.
UNESCO's progression levels are Acquire / Deepen / Create for teachers and Understand / Apply /
Create for students.

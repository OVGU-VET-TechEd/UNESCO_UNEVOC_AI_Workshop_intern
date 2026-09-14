# C — Pilot selection worksheet

*A facilitation artefact. Print one copy per candidate use case and work through it in the room. It
takes about 25 minutes per candidate and is designed to stop bad pilots before they start rather than
to sell good ones.*

---

## Part 1 — Describe the job (5 min)

Fill this in before scoring anything. If you cannot fill it in, that is the finding.

| | |
|---|---|
| **Candidate use case** | |
| **Who does this job today** | |
| **How often** | |
| **How long it takes, per instance** | |
| **What "done" looks like today** | |
| **Who is accountable for the output** | |
| **What goes wrong when it goes wrong** | |

---

## Part 2 — Score it (10 min)

Score each row 0, 1 or 2. Be strict; optimism here is paid for later.

| # | Question | 0 | 1 | 2 | Score |
|---|---|---|---|---|---|
| 1 | **Are the criteria written down?** | Only in people's heads | Partly written | Fully written and versioned | |
| 2 | **Is there a machine-checkable definition of done?** | No | Partly — some checks possible | Yes — a command or comparison that passes or fails | |
| 3 | **Do the source documents exist in one place?** | Scattered, unknown | Findable with effort | Already in one folder | |
| 4 | **Is their status clear (current vs superseded)?** | No | Some dated | All dated, superseded material identifiable | |
| 5 | **Can the documents be used?** (cleared, public, or anonymisable) | Unclear or needs approval nobody will give | Approval plausible | Already public or already cleared | |
| 6 | **Is there a manual baseline to compare against?** | None | Anecdotal | Measured — hours, error rate, or both | |
| 7 | **Is there a named owner for the corpus after the pilot?** | Nobody | Someone, informally | Named, with time allocated | |
| 8 | **Is the human decision preserved?** | The system would decide | Human reviews samples | Human approves every output | |
| 9 | **What happens if the system refuses?** | Undefined | Someone probably notices | Defined fallback path | |
| 10 | **Would a wrong output be visible?** | No — it would look fine | Probably caught downstream | Yes — verification would catch it | |

**Total (0–20):** ______

### Reading the score

| Total | Verdict |
|---|---|
| **16–20** | Good pilot candidate. Proceed. |
| **11–15** | Viable, but fix the lowest-scoring rows first. Rows 1, 2 and 5 are the ones to fix before starting, not during. |
| **6–10** | Not yet a pilot. It is a documentation project. That project is worth doing anyway, and it is the prerequisite. |
| **0–5** | Do not start. Nothing here will be improved by adding a language model. |

> **The most common pattern.** A candidate scores well on rows 3, 6 and 8 and badly on rows 1, 2 and
> 4. That combination means the *work* is well understood but the *criteria* are not written down.
> The right response is to write the checklist. Doing so is useful with or without AI, and it is the
> single highest-return activity in this whole area.

---

## Part 3 — Scope it (10 min)

Only if the score was 11 or above.

| | |
|---|---|
| **Pattern** (assistant / assistant+KB / semi-agent / agent — see File A §3) | |
| **Corpus: how many documents, from where** | |
| **Clearance route for those documents** | |
| **Question or task set: how many, collected from whom, collected when** | |
| **Success criterion, as a number** | |
| **Failure criterion — what result would make you stop** | |
| **Duration** | |
| **Who runs it** | |
| **Who owns the corpus afterwards** | |
| **What is explicitly out of scope** | |

### Two fields people leave blank, and should not

**Failure criterion.** Write down, in advance, the result that would make you stop. A pilot without a
stated failure criterion cannot fail, and therefore cannot inform a decision. Example: *"if writing
the review checklist takes longer than the reviews it saves in the pilot period, we stop and keep the
checklist."*

**What is explicitly out of scope.** Scope grows during pilots, always in the direction of "and could
it also…". Name three things it will not do.

---

## Part 4 — The five questions to ask any vendor

If a supplied product is under consideration rather than an internal build, these five questions
separate substance from presentation. They map directly onto the definitions in File A.

1. **"When it cannot answer, what does it do?"** If there is no defined refusal behaviour, it
   produces a plausible answer to every question, including the ones your documents do not cover.
2. **"Show me an answer with its sources, and let me open the source."** Citation that cannot be
   opened and checked is decoration.
3. **"How do I update the knowledge base, and how long does it take?"** If the answer involves
   retraining, or takes weeks, corpus hygiene will not happen and the system will go stale.
4. **"What is your refusal rate on questions outside the corpus, measured how?"** Vendors publish
   accuracy on questions they can answer. The interesting number is the other one.
5. **"Where does our data go, and what is retained?"** Distinct from "is it encrypted". Ask what is
   stored, by whom, for how long, and whether it is used for training.

A supplier who answers all five concretely is worth talking to. One who redirects to capability
demonstrations is selling the model, and the model is the part that is roughly the same for everyone.

---

## UNESCO framework alignment

This worksheet is *Create*-level activity under the **UNESCO AI competency framework for teachers**
(2024), aspects *AI pedagogy* and *human-centred mindset*: designing an AI-supported workflow for
your own context, and deciding deliberately where human judgement must remain. Row 8 of the scoring
table — is the human decision preserved — is the framework's human-agency principle expressed as a
procurement question. UNESCO's progression levels are Acquire / Deepen / Create for teachers and
Understand / Apply / Create for students.

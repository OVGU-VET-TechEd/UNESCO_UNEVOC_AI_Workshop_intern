# Evaluation report

Run 2026-09-15 17:59 · model `mock:demo` · knowledge base `kb.json` · embeddings `none` · 41 passages from 8 documents · 0 s

## Headline numbers

| Measure | Result | What it means |
|---|---|---|
| Retrieval hit rate | **100%** (9/9) | the expected document reached the prompt. If this is low, fix chunking or retrieval, not the model. |
| Answered when it should | **100%** (9/9) | questions the corpus covers actually got an answer. |
| Refused when it should | **100%** (3/3) | questions outside the corpus were declined rather than invented. |
| Answers needing a retry | 2/12 | the citation check rejected a first attempt. |

Report these three separately. A single blended figure hides which one broke.

## Per question

| # | Question | Expected | Result | Right doc retrieved | Top passage |
|---|---|---|---|---|---|
| 1 | What kinds of evidence are acceptable for quality assurance self-assessment? | answered | answered | yes | 01_tvet_quality_framework.md (17.86) |
| 2 | How often does full external review of a centre take place? | answered | answered | yes | 01_tvet_quality_framework.md (12.33) |
| 3 | Can a microcredential be issued without a stated assessment method? | answered | answered | yes | 02_microcredential_guidelines.md (20.21) |
| 4 | What is the minimum interoperability target for packaging credentials? | answered | answered | yes | 02_microcredential_guidelines.md (16.41) |
| 5 | Which project milestone has slipped, and what was the reason given? | answered | answered | yes | 04_progress_report_q3.md (9.78) |
| 6 | How many learners completed at partner B? | answered | answered | yes | 04_progress_report_q3.md (9.59) |
| 7 | What claims can the evaluation not support, and why? | answered | answered | yes | 06_evaluation_methodology_note.md (10.86) |
| 8 | What must be checked before a module is published, regarding licensing? | answered | answered | yes | 08_open_licensing_note.md (13.38) |
| 9 | How is the instructor training assessed? | answered | answered | yes | 05_instructor_training_outline.md (7.68) |
| 10 | What is the capital city of Peru? | refused | refused_no_evidence | — | 06_evaluation_methodology_note.md (4.64) |
| 11 | What was the exact salary of the project coordinator last year? | refused | refused_no_evidence | — | 02_microcredential_guidelines.md (9.8) |
| 12 | Which brand of welding helmet should we purchase for the workshop? | refused | refused_no_evidence | — | 05_instructor_training_outline.md (4.93) |

## Answers in full

**1. What kinds of evidence are acceptable for quality assurance self-assessment?**

> According to the documents, Self-assessment must be supported by evidence. Acceptable evidence includes completion and progression data, employer feedback, staff qualification records, and equipment inspection reports. Learner s [S1]

**2. How often does full external review of a centre take place?**

> According to the documents, Full external review takes place every four years. A lighter self-assessment is submitted annually by 31 March. Centres holding conditional recognition submit self-assessment every six months until th [S1]

**3. Can a microcredential be issued without a stated assessment method?**

> According to the documents, Every microcredential must state: the learning outcomes, the notional learning hours, the assessment method, the level, and the issuing body. Learning outcomes must be written as observable statements [S1]

**4. What is the minimum interoperability target for packaging credentials?**

> According to the documents, Credentials should be issued in a machine-readable format that carries the issuer, the holder, the outcomes and the issue date. Where a learning management system is used, SCORM 1.2 remains the minimu [S1]

**5. Which project milestone has slipped, and what was the reason given?**

> According to the documents, The project is broadly on schedule. Three of five milestones due by the end of the quarter were met in full, one was met in part, and one has slipped. | Milestone | Planned | Actual | Status | |---|-- [S1]

**6. How many learners completed at partner B?**

> According to the documents, | Partner | Enrolled | Completed | |---|---|---| | Partner A | 84 | 71 | | Partner B | 62 | 55 | | Partner C | 0 | 0 | | Partner D | 77 | 69 | [S2] (from 03_project_charter_greenskills.md, section "Mi [S1]

**7. What claims can the evaluation not support, and why?**

> According to the documents, Completion rates, learner satisfaction, and instructor-reported changes in practice can be reported directly as observations. [S2] (from 06_evaluation_methodology_note.md, section "Purpose") This note [S1]

**8. What must be checked before a module is published, regarding licensing?**

> According to the documents, Before publishing any module, check the materials register for third-party items. A module containing an unlisted third-party image may not be published until the item is either licensed, replaced, or [S1]

**9. How is the instructor training assessed?**

> According to the documents, Participants are assessed on the module they produce, against a published rubric. There is no written examination. [S2] (from 05_instructor_training_outline.md, section "Day 1 — Content and outcomes") [S1]

**10. What is the capital city of Peru?**

> I could not find anything in the knowledge base that answers this. Nothing has been made up. Either the documents do not cover it, or the question uses different words than the documents do.

**11. What was the exact salary of the project coordinator last year?**

> I could not find anything in the knowledge base that answers this. Nothing has been made up. Either the documents do not cover it, or the question uses different words than the documents do.

**12. Which brand of welding helmet should we purchase for the workshop?**

> I could not find anything in the knowledge base that answers this. Nothing has been made up. Either the documents do not cover it, or the question uses different words than the documents do.

---

**What this report does not tell you.** Whether the prose is good, whether a correct citation was used correctly, or whether the answer is useful for the job someone actually has. Those require a person to read the answers above. This harness tells you where to look.

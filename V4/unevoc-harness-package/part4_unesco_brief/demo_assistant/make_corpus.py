#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_corpus.py — create the demo corpus.

Run once:

    python make_corpus.py

It writes eight short documents into ./corpus_raw/ .

IMPORTANT — WHAT THESE DOCUMENTS ARE
    They are SYNTHETIC. They were written for this demonstration. They are not
    UNESCO or UNEVOC documents, they contain no real policy, no real project data
    and no real people. The names, email addresses and phone numbers in
    `07_steering_minutes.md` are invented, and they are there for exactly one
    reason: so that `anonymise.py` has something to remove in front of an
    audience.

    When you run this for real, delete ./corpus_raw/ and put your own documents
    there instead. The pipeline reads .md, .txt and .pdf.

WHY A "RAW" FOLDER
    The pipeline is deliberately three folders, not one:

        corpus_raw/    what you were given          (never indexed directly)
        corpus/        anonymised, ready to index   (produced by anonymise.py)
        kb.json        the knowledge base           (produced by kb_build.py)

    Keeping them separate means "has this been through the scrubber?" is a
    question you answer by looking at a path, not by remembering.
"""

from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "corpus_raw")

DOCS: dict[str, str] = {
"01_tvet_quality_framework.md": """# Regional TVET Quality Assurance Framework (synthetic sample)

## 1. Purpose

This framework describes how participating centres assure the quality of technical and
vocational training provision. It applies to all publicly funded programmes of 120 hours
or more. It does not apply to short awareness courses of fewer than 20 hours.

## 2. Quality dimensions

Provision is assessed against five dimensions: relevance to labour market need,
learner outcomes, staff competence, facilities and equipment, and inclusion.

Each dimension is rated on a four-point scale: not established, emerging, established,
advanced. A centre must reach "established" on all five dimensions to hold full
recognition. A centre rated "emerging" on any dimension receives conditional
recognition for twelve months.

## 3. Review cycle

Full external review takes place every four years. A lighter self-assessment is
submitted annually by 31 March. Centres holding conditional recognition submit
self-assessment every six months until the condition is lifted.

## 4. Evidence

Self-assessment must be supported by evidence. Acceptable evidence includes completion
and progression data, employer feedback, staff qualification records, and equipment
inspection reports. Learner satisfaction surveys alone are not sufficient evidence for
any dimension.

## 5. Appeals

A centre may appeal a rating within 30 calendar days of notification. Appeals are heard
by a panel that did not take part in the original review.
""",

"02_microcredential_guidelines.md": """# Guidelines for Microcredential Design (synthetic sample)

## Scope

These guidelines cover microcredentials of between 5 and 60 notional learning hours
offered by participating centres.

## Required elements

Every microcredential must state: the learning outcomes, the notional learning hours,
the assessment method, the level, and the issuing body. Learning outcomes must be
written as observable statements beginning with an action verb.

A microcredential without a stated assessment method may not be issued. Attendance is
not an assessment method.

## Stacking

Microcredentials may be stacked toward a larger qualification only where the issuing
body has published a stacking rule in advance. Retrospective stacking is not permitted.

## Digital format

Credentials should be issued in a machine-readable format that carries the issuer, the
holder, the outcomes and the issue date. Where a learning management system is used,
SCORM 1.2 remains the minimum interoperability target for participating centres,
although newer packaging formats are encouraged.

## Review

Guidelines are reviewed every two years. The current version was adopted in the third
quarter of the reporting year.
""",

"03_project_charter_greenskills.md": """# Project Charter — Green Skills for Manufacturing (synthetic sample)

## Summary

A 24-month project to develop and pilot six microcredentials in energy-efficient
manufacturing practice across four partner centres.

## Objectives

1. Map green-skill gaps in the regional manufacturing sector.
2. Develop six microcredentials of 20 to 40 notional hours each.
3. Train 24 instructors to deliver them.
4. Pilot with at least 300 learners.
5. Publish an open evaluation report.

## Milestones

| Milestone | Due | Owner |
|---|---|---|
| Skills gap report published | Month 4 | Work package 1 lead |
| First two microcredentials drafted | Month 9 | Work package 2 lead |
| Instructor training delivered | Month 13 | Work package 3 lead |
| Pilot completed, 300 learners | Month 20 | Work package 4 lead |
| Evaluation report published | Month 23 | Coordinator |

## Budget summary

| Category | Share of total |
|---|---|
| Staff | 62 |
| Equipment | 14 |
| Travel | 9 |
| Dissemination | 8 |
| Indirect | 7 |

## Risks

The most significant identified risk is instructor availability during the pilot term.
A secondary risk is that equipment procurement in one partner country exceeds the
planned lead time of eight weeks.
""",

"04_progress_report_q3.md": """# Progress Report — Green Skills for Manufacturing, Quarter 3 (synthetic sample)

## Status summary

The project is broadly on schedule. Three of five milestones due by the end of the
quarter were met in full, one was met in part, and one has slipped.

| Milestone | Planned | Actual | Status |
|---|---|---|---|
| Skills gap report published | Month 4 | Month 4 | Met |
| Partner agreements signed | Month 5 | Month 5 | Met |
| Instructor recruitment complete | Month 7 | Month 7 | Met |
| First two microcredentials drafted | Month 9 | Month 10 | Partly met |
| Equipment installed at partner C | Month 8 | not yet | Slipped |

## Explanation of variance

Drafting of the first two microcredentials took one month longer than planned because
the assessment design required a second review round against the microcredential
guidelines. The content is now complete and has passed review.

Equipment installation at partner C has slipped by an estimated ten weeks. The cause is
a customs delay, not a procurement failure. Mitigation: the pilot at partner C will
begin with the two microcredentials that do not require the delayed equipment.

## Learner numbers

| Partner | Enrolled | Completed |
|---|---|---|
| Partner A | 84 | 71 |
| Partner B | 62 | 55 |
| Partner C | 0 | 0 |
| Partner D | 77 | 69 |

## Next quarter

Complete drafting of microcredentials three and four, begin instructor training, and
confirm a revised equipment date with partner C.
""",

"05_instructor_training_outline.md": """# Instructor Training — Outline (synthetic sample)

## Audience

Vocational instructors delivering the green-skills microcredentials. No prior experience
of digital course authoring is assumed.

## Duration

Three days, delivered face to face, with a half-day follow-up after six weeks.

## Day 1 — Content and outcomes

Writing observable learning outcomes. Aligning assessment to outcomes. Common failure
modes: outcomes that cannot be assessed, and assessments that test recall when the
outcome asks for application.

## Day 2 — Delivery and assessment

Practical workshop delivery. Formative versus summative assessment. Recording evidence
for quality assurance purposes.

## Day 3 — Digital authoring and packaging

Authoring a module in a plain-text format. Adding a quiz. Exporting to the learning
management system. Participants finish the day with one complete module of their own.

## Follow-up

A half-day session six weeks later reviews what participants actually delivered and
what went wrong.

## Assessment of participants

Participants are assessed on the module they produce, against a published rubric. There
is no written examination.
""",

"06_evaluation_methodology_note.md": """# Evaluation Methodology Note (synthetic sample)

## Purpose

This note records how the project's evaluation claims should and should not be phrased.

## Design

The pilot is not a controlled trial. There is no comparison group. Learners self-select
into the microcredentials, and partner centres differ in size, sector focus and prior
provision.

## What can be claimed

Completion rates, learner satisfaction, and instructor-reported changes in practice can
be reported directly as observations.

## What cannot be claimed

Any statement of the form "the microcredential caused an improvement in employment
outcomes" cannot be supported by this design. Where employment data is collected, it
should be reported as an association and explicitly labelled as such.

## Sample size

The planned pilot of 300 learners is adequate for descriptive reporting. It is not
adequate for subgroup analysis by sector, and subgroup figures should be reported with
counts rather than percentages where the subgroup is smaller than 30.

## Data protection

No personal data leaves the partner centre. Aggregated figures only are transmitted to
the coordinator.
""",

"07_steering_minutes.md": """# Steering Committee Minutes — Quarter 3 (synthetic sample, contains invented personal data)

Date: 14 October
Chair: Dr Maria Sanchez (maria.sanchez@example-partner.org, +49 391 555 0142)
Present: Dr Maria Sanchez, Ing. Tomas Novak (t.novak@example-centre.cz), Ms Amina Diallo
(amina.diallo@example-college.sn, +221 77 555 0198), Mr Peter Berg
Apologies: Ms Lena Okafor

## 1. Minutes of the previous meeting

Approved without amendment.

## 2. Equipment delay at partner C

Ing. Tomas Novak reported the customs delay. The committee agreed the mitigation set out
in the quarterly progress report: begin the pilot with the two microcredentials that do
not require the delayed equipment.

Action: Mr Peter Berg to confirm a revised installation date by 5 November.

## 3. Microcredential review round

Ms Amina Diallo noted that the second review round improved assessment design and
recommended building the second round into the schedule for the remaining four
microcredentials rather than treating it as an exception.

Decision: the schedule will be revised to include two review rounds per microcredential.

## 4. Any other business

The committee noted that the evaluation methodology note should be circulated to all
partners before employment data is collected.

Next meeting: 16 January.
""",

"08_open_licensing_note.md": """# Open Licensing Note (synthetic sample)

## Default

Materials produced by the project are released under an open licence permitting reuse
and adaptation with attribution, unless a specific exception is recorded.

## Exceptions

Two categories are excepted. First, third-party material included under a separate
licence, which retains its own terms and must be listed in the materials register.
Second, assessment instruments, which are released to partner centres only, because
public release would compromise their use.

## Attribution

Attribution must name the project and the licence. It need not name individual authors,
although it may.

## Practical consequence

Before publishing any module, check the materials register for third-party items. A
module containing an unlisted third-party image may not be published until the item is
either licensed, replaced, or removed.
""",
}


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for name, text in DOCS.items():
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {name}  ({len(text)} characters)")
    print(f"\n{len(DOCS)} synthetic documents in {OUT}")
    print("These are invented for the demo. Replace them with your own before real use.")
    print("\nNext:  python anonymise.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

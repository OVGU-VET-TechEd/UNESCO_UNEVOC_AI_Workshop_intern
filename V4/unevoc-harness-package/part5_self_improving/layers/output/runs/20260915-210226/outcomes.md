# Lab outcomes — llama3.1:8b

> Real run on this computer. Every figure below was measured during this run; nothing is replayed from the HTML page.

| | |
|---|---|
| Model | `llama3.1:8b` (8.0B, Q4_K_M, digest 46e0c10c039e) |
| Ollama | 0.34.0 at http://127.0.0.1:11434 |
| Machine | macOS-26.6.2-x86_64-i386-64bit, Python 3.10.9 |
| Run | 2026-09-15T21:02:26 → 2026-09-15T21:03:08 (42.5 s) |

## Summary

| Lab | What | Runs | Exit codes | Seconds | As expected | Outcome |
|---|---|---:|---|---:|---|---|
| 0 | Tokens | 1 | 0 | 1.6 | yes | English 10 tokens (1.25/word, page est. 14); German 18 tokens (2.57/word, page est. 17); French 23 tokens (2.3/word, page est. 26); Spanish 20 tokens (1.67/word, page est. 22) |
| 1 | Prompt: vague vs. specific | 1 | 0 | 4.5 | yes | vague: passed 0/1; specific: passed 1/1 |
| 2 | Skill: without vs. with SKILL.md | 1 | 0 | 2.4 | yes | without skill: passed 0/1; with skill: passed 1/1 |
| 3 | Harness: make verify | 1 | 0 | 0.2 | yes | verify exit 0: 15 ok line(s), 0 failure(s) |
| 3b | Harness: verify with a planted leak | 1 | 0 | 0.2 | yes | planted email caught (verify exit 1); corpus restored: True |
| 4 | Loop: agent.py | 1 | 0 | 18.6 | yes | 11 steps, 7 override(s), stop condition met; model in state.json: llama3.1:8b |
| 5 | Self-improving: wiki_agent.py | 1 | 0 | 15.1 | yes | baseline 0% -> final 100% over 1 iteration(s); 1 kept, 0 rolled back; 1 wiki page(s) |

"As expected" means the lab showed what the page claims: the specific prompt and the skill do at least as well as their counterparts, verify passes, the planted leak is caught, the agent stops by its stop condition, and evolution ends above its baseline. A "no" is a real result, not a script error: read that lab's section.

## Lab 0 — Tokens

`python layer0_tokens.py --model llama3.1:8b`

| Language | Words | Page estimate | Real tokens | Tokens/word |
|---|---:|---:|---:|---:|
| English | 8 | 14 | 10 | 1.25 |
| German | 7 | 17 | 18 | 2.57 |
| French | 10 | 26 | 23 | 2.3 |
| Spanish | 12 | 22 | 20 | 1.67 |

Logs: `logs/layer0_tokens.log`

## Lab 1 — Prompt: vague vs. specific

`python layer1_prompt.py --model llama3.1:8b`

| Run | Variant | Passed | Reason | Words | Prompt tok | Answer tok | Seconds | Answer |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | vague | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 141 | 18 | 175 | 3.78 | Here is a sample learning objective about hydraulic safety:  **Learning Objective:**  Upon completion of this training, the learner will be able to identify ... |
| 1 | specific | yes | ok | 18 | 49 | 21 | 0.59 | Identify and assess potential hazards associated with hydraulic system operation and maintenance procedures to ensure safe working practices. |

Logs: `logs/layer1_prompt.log`

## Lab 2 — Skill: without vs. with SKILL.md

`python layer2_skill.py --model llama3.1:8b`

| Run | Variant | Passed | Reason | Words | Prompt tok | Answer tok | Seconds | Answer |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | without skill | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 58 | 27 | 72 | 1.65 | Here is a potential learning objective for a vocational training module on hydraulic system safety:  **Learning Objective:**  Upon completion of this module,... |
| 1 | with skill | yes | ok | 13 | 102 | 16 | 0.63 | Identify potential hazards in hydraulic systems to ensure safe operation and maintenance practices. |

Logs: `logs/layer2_skill.log`

## Lab 3 — Harness: make verify

`python layer3_harness.py --model llama3.1:8b`

- verify exit code: **0**
- ok lines: 15
- no failures

Logs: `logs/layer3_harness.log`

## Lab 3b — Harness: verify with a planted leak

`python layer3_harness.py --model llama3.1:8b --break`

- verify exit code: **1**
- ok lines: 14
- FAIL [anonymisation] corpus/07_steering_minutes.md still contains an unredacted email: maria.sanchez@example-partner.org

Logs: `logs/layer3_harness_break.log`

## Lab 4 — Loop: agent.py

`python layer4_loop.py --model llama3.1:8b`

- steps: 11
- overrides: 7
- stop condition met: True
- hit the 40-step limit: False
- PDFs: 3, report written: True
- override reason: the PDFs have already been listed
- override reason: `summarise_md` is not one of my five tools
- override reason: `summarise_md` is not one of my five tools
- override reason: `summarise_md` is not one of my five tools
- override reason: `summarise_md` is not one of my five tools
- override reason: site_a_workshop_report.pdf has already had `summarize_md` applied
- override reason: site_b_hydraulics_report.pdf has already had `summarize_md` applied

| PDF | Summary written by the model |
|---|---|
| site_a_workshop_report.pdf | The site A metal workshop annual safety and training report covers the four quarters of the reporting year and summarises recorded incidents and training hours. The report shows a total of 17 incidents, with the majority occurring in the first quarter, and a significant increase in training hours in the third quarter due to the introduction of a revised hot-work induction. The annual equipment inspection recorded two non-conformities, both related to extraction airflow in bays three and four. |
| site_b_hydraulics_report.pdf | The document is a safety and training report for the hydraulics laboratory at Site B, which is used for pressure-system training. The report shows a reduction in incidents from 9 in the first quarter to 4 in the third and fourth quarters, although the replacement of an older test rig in the second quarter is cited as a possible explanation. The report also notes that training hours remained relatively stable throughout the year, ranging from 155 to 180 hours per quarter. |
| site_c_electrical_report.pdf | The Site C Electrical Report documents the annual safety and training performance of the Site C Electrical Training Centre. The centre recorded a low incident count throughout the year, with only one incident in the third quarter involving a hand tool rather than an electrical hazard. The training hours dipped in the fourth quarter due to the examination period, but no non-conformities were recorded at the annual inspection. |

Logs: `logs/layer4_loop.log`

## Lab 5 — Self-improving: wiki_agent.py

`python layer5_evolve.py --model llama3.1:8b --iterations 5`

| Iteration | Rollout score | Validation score | Previous best | Skill lines | Gate |
|---:|---:|---:|---:|---:|---|
| 1 | 0% | 100% | 0% | 23 | KEPT |

Wiki pages: `opened-with-x-not-an-approved-action-verb.md`

Final SKILL.md:

```text
---
# Pattern: opened with 'X', not an approved action verb

**First seen:** iteration 1

**What happens:** the answer is rejected because opened with 'X', not an approved action verb.

**Example:** `Upon completion of this module, the apprentice mechanic will be able to identify and describe the key safety procedures for working with hydraulic systems, incl`

**Proposed rules:**

* Use approved action verbs to begin each learning objective, such as "Identify", "Describe", "Explain", "Demonstrate", "Apply", or "Analyze".
* Replace "Upon completion of this module" with a more specific description of the learning outcome.
* Ensure that each learning objective is specific, measurable, achievable, relevant, and time-bound (SMART).
* Use a consistent verb tense throughout the learning objective.
* Avoid using phrases that imply the learner will "be able to" do something, instead focus on what they will actually do.
* Remove any unnecessary words or phrases that do not add value to the learning objective.
* Use present tense for learning objectives that describe a future action.
* Ensure that the learning objective is concise and easy to understand.

## Evidence

- Iteration 1: 4 occurrence(s).
```

Logs: `logs/layer5_evolve.log`

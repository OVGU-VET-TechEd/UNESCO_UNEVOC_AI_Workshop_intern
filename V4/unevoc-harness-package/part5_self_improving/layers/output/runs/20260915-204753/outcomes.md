# Lab outcomes — llama3.1:8b

> Real run on this computer. Every figure below was measured during this run; nothing is replayed from the HTML page.

| | |
|---|---|
| Model | `llama3.1:8b` (8.0B, Q4_K_M, digest 46e0c10c039e) |
| Ollama | 0.34.0 at http://127.0.0.1:11434 |
| Machine | macOS-26.6.2-x86_64-i386-64bit, Python 3.10.9 |
| Run | 2026-09-15T20:47:53 → 2026-09-15T20:52:09 (255.6 s) |

## Summary

| Lab | What | Runs | Exit codes | Seconds | As expected | Outcome |
|---|---|---:|---|---:|---|---|
| 0 | Tokens | 1 | 0 | 29.9 | yes | English 10 tokens (1.25/word, page est. 14); German 18 tokens (2.57/word, page est. 17); French 23 tokens (2.3/word, page est. 26); Spanish 20 tokens (1.67/word, page est. 22) |
| 1 | Prompt: vague vs. specific | 1 | 0 | 25.3 | yes | vague: passed 0/1; specific: passed 1/1 |
| 2 | Skill: without vs. with SKILL.md | 1 | 0 | 29.4 | yes | without skill: passed 0/1; with skill: passed 1/1 |
| 3 | Harness: make verify | 1 | 0 | 0.2 | yes | verify exit 0: 15 ok line(s), 0 failure(s) |
| 3b | Harness: verify with a planted leak | 1 | 0 | 0.2 | yes | planted email caught (verify exit 1); corpus restored: True |
| 4 | Loop: agent.py | 1 | 0 | 109.6 | yes | 11 steps, 7 override(s), stop condition met; model in state.json: llama3.1:8b |
| 5 | Self-improving: wiki_agent.py | 1 | 0 | 61.0 | yes | baseline 0% -> final 0% over 5 iteration(s); 0 kept, 5 rolled back; 1 wiki page(s) |

"As expected" means the lab showed what the page claims: the specific prompt and the skill do at least as well as their counterparts, verify passes, the planted leak is caught, the agent stops by its stop condition, and evolution does not end below its baseline.

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
| 1 | vague | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 143 | 18 | 185 | 13.68 | Here is a potential learning objective about hydraulic safety:  **Learning Objective:**  Upon completion of this training, learners will be able to identify ... |
| 1 | specific | yes | ok | 14 | 49 | 17 | 11.55 | Identify and explain the key hazards associated with hydraulic system operation and maintenance procedures. |

Logs: `logs/layer1_prompt.log`

## Lab 2 — Skill: without vs. with SKILL.md

`python layer2_skill.py --model llama3.1:8b`

| Run | Variant | Passed | Reason | Words | Prompt tok | Answer tok | Seconds | Answer |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | without skill | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 61 | 27 | 75 | 16.93 | Here is a potential learning objective for a vocational training module on hydraulic system safety:  **Learning Objective:**  Upon completion of this module,... |
| 1 | with skill | yes | ok | 14 | 102 | 17 | 12.32 | Identify potential hazards in hydraulic systems and describe appropriate safety measures to mitigate risks. |

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
- override reason: site_a_workshop_report.pdf has already had `summarize_md` applied
- override reason: site_b_hydraulics_report.pdf has already had `summarize_md` applied

| PDF | Summary written by the model |
|---|---|
| site_a_workshop_report.pdf | The site A metal workshop annual safety and training report covers the four quarters of the reporting year, summarising recorded incidents, delivered training hours, and the outcome of the annual equipment inspection. The report shows a total of 17 incidents recorded over the year, with a significant increase in training hours in the third quarter due to the introduction of a revised hot-work induction. The annual inspection identified two non-conformities related to extraction airflow, which were addressed before the end of the year. |
| site_b_hydraulics_report.pdf | The document is the Site B Hydraulics Report, which outlines the safety and training record for the hydraulics laboratory at Site B. The report shows a reduction in incidents from 9 in the first quarter to 4 in the third and fourth quarters, with a corresponding increase in training hours. The replacement of an older test rig in the second quarter is cited as a possible explanation for the reduction in incidents. |
| site_c_electrical_report.pdf | The Site C Electrical Report documents the annual safety and training performance of the Site C Electrical Training Centre. The centre recorded a low incident count throughout the year, with a total of 4 incidents, and no non-conformities were found during the annual inspection. Training hours dipped in the fourth quarter due to the examination period, but overall the centre's performance was consistent with its de-energised training model. |

Logs: `logs/layer4_loop.log`

## Lab 5 — Self-improving: wiki_agent.py

`python layer5_evolve.py --model llama3.1:8b --iterations 5`

| Iteration | Rollout score | Validation score | Previous best | Skill lines | Gate |
|---:|---:|---:|---:|---:|---|
| 1 | 0% | 0% | 0% | 19 | ROLLED BACK |
| 2 | 0% | 0% | 0% | 25 | ROLLED BACK |
| 3 | 0% | 0% | 0% | 27 | ROLLED BACK |
| 4 | 0% | 0% | 0% | 29 | ROLLED BACK |
| 5 | 0% | 0% | 0% | 31 | ROLLED BACK |

Wiki pages: `opened-with-x-not-an-approved-action-verb.md`

Logs: `logs/layer5_evolve.log`

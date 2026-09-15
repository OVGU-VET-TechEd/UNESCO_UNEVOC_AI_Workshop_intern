# Lab outcomes — llama3.1:8b

> Real run on this computer. Every figure below was measured during this run; nothing is replayed from the HTML page.

| | |
|---|---|
| Model | `llama3.1:8b` (8.0B, Q4_K_M, digest 46e0c10c039e) |
| Ollama | 0.34.0 at http://127.0.0.1:11434 |
| Machine | macOS-26.6.2-x86_64-i386-64bit, Python 3.10.9 |
| Run | 2026-09-15T20:43:18 → 2026-09-15T20:45:53 (154.3 s) |

## Summary

| Lab | What | Runs | Exit codes | Seconds | As expected | Outcome |
|---|---|---:|---|---:|---|---|
| 0 | Tokens | 1 | 0 | 47.5 | yes | English 10 tokens (1.25/word, page est. 14); German 18 tokens (2.57/word, page est. 17); French 23 tokens (2.3/word, page est. 26); Spanish 20 tokens (1.67/word, page est. 22) |
| 1 | Prompt: vague vs. specific | 2 | 0, 0 | 68.8 | yes | vague: passed 0/2; specific: passed 2/2 |
| 2 | Skill: without vs. with SKILL.md | 2 | 0, 0 | 37.3 | yes | without skill: passed 0/2; with skill: passed 2/2 |
| 3 | Harness: make verify | 1 | 0 | 0.2 | yes | verify exit 0: 15 ok line(s), 0 failure(s) |
| 3b | Harness: verify with a planted leak | 1 | 0 | 0.2 | yes | planted email caught (verify exit 1); corpus restored: True |

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
| 1 | vague | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 146 | 18 | 182 | 18.9 | Here is a sample learning objective about hydraulic safety:  **Learning Objective:**  Upon completion of this training, the learner will be able to identify ... |
| 1 | specific | yes | ok | 14 | 49 | 17 | 16.42 | Identify and explain the key hazards associated with hydraulic system operation and maintenance procedures. |
| 2 | vague | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 109 | 18 | 136 | 20.68 | Here is a sample learning objective about hydraulic safety:  **Learning Objective:**  Upon completion of this training, the learner will be able to identify ... |
| 2 | specific | yes | ok | 14 | 49 | 17 | 12.49 | Identify and assess potential hazards associated with hydraulic systems to prevent accidents and injuries. |

Logs: `logs/layer1_prompt_run1.log`, `logs/layer1_prompt_run2.log`

## Lab 2 — Skill: without vs. with SKILL.md

`python layer2_skill.py --model llama3.1:8b`

| Run | Variant | Passed | Reason | Words | Prompt tok | Answer tok | Seconds | Answer |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | without skill | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 57 | 27 | 71 | 5.86 | Here is a potential learning objective for a vocational training module on hydraulic system safety:  **Learning Objective:**  Upon completion of this module,... |
| 1 | with skill | yes | ok | 12 | 102 | 15 | 11.27 | Identify potential hazards in hydraulic systems and describe measures to mitigate risks. |
| 2 | without skill | no | it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate) | 61 | 27 | 75 | 8.86 | Here is a potential learning objective for a vocational training module on hydraulic system safety:  **Learning Objective:**  Upon completion of this module,... |
| 2 | with skill | yes | ok | 11 | 102 | 14 | 11.04 | Identify potential hazards associated with hydraulic system operation and maintenance procedures. |

Logs: `logs/layer2_skill_run1.log`, `logs/layer2_skill_run2.log`

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

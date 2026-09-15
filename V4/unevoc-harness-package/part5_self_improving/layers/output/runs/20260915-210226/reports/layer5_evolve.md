# Layer 5 — self-improving agent

> Generated on this computer by the local model `llama3.1:8b` via http://127.0.0.1:11434.  
> Run: 2026-09-15 21:03

`wiki_agent.py --model llama3.1:8b --reset --iterations 5` exited with code 0.

## The skill it wrote for itself

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

## wiki/patterns/opened-with-x-not-an-approved-action-verb.md

```text
# Pattern: opened with 'X', not an approved action verb

**First seen:** iteration 1

**What happens:** the answer is rejected because opened with 'X', not an approved action verb.

**Example:** `Upon completion of this module, the apprentice mechanic will be able to identify and describe the key safety procedures for working with hydraulic systems, incl`

**Proposed rule:** Approved action verbs must be used to begin each learning objective, such as "Identify", "Describe", "Explain", "Demonstrate", "Apply", or "Analyze".

## Evidence

- Iteration 1: 4 occurrence(s).
```

## wiki/skill-impact.md

```text

## Iteration 1 — ACCEPTED

- Validation score: 100% (previous best 0%)
- Skill length: 23 lines
- Outcome: kept
```

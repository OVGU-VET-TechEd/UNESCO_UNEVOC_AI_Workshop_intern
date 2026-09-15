# Layer 2 — skill engineering

> Generated on this computer by the local model `llama3.1:8b` via http://127.0.0.1:11434.  
> Run: 2026-09-15 20:45

Skill file: `part5_self_improving/layers/skills/objectives/SKILL.md`

```text
---
name: objectives
description: House rules for writing learning objectives in vocational training modules.
---
# Writing learning objectives
- Begin with an approved action verb (identify, describe, explain, demonstrate, inspect, assess).
- Use at most 20 words.
- Write exactly one sentence.
- Reply with the sentence only, no preamble.
```

## Skill file: not loaded

**Prompt sent** (27 tokens):

```text
Task: Write one learning objective for a vocational training module on: hydraulic system safety.
```

**Reply:**

```text
Here is a potential learning objective for a vocational training module on hydraulic system safety:

**Learning Objective:**

Upon completion of this module, learners will be able to identify and mitigate potential hazards associated with hydraulic system operation, including proper lockout/tagout procedures, personal protective equipment requirements, and safe system maintenance practices, in order to prevent injury and ensure a safe working environment.
```

**Check:** Fails: it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate).

## Skill file: loaded

**Prompt sent** (102 tokens):

```text
Follow this guidance exactly:
---
---
name: objectives
description: House rules for writing learning objectives in vocational training modules.
---
# Writing learning objectives
- Begin with an approved action verb (identify, describe, explain, demonstrate, inspect, assess).
- Use at most 20 words.
- Write exactly one sentence.
- Reply with the sentence only, no preamble.
---

Task: Write one learning objective for a vocational training module on: hydraulic system safety.
```

**Reply:**

```text
Identify potential hazards associated with hydraulic system operation and maintenance procedures.
```

**Check:** Passes all three house rules.

Same model, same task. Only the skill block differed. A capable model may pass even without the skill — run it several times, or with a smaller model (e.g. `phi3`), to see the difference the file makes.

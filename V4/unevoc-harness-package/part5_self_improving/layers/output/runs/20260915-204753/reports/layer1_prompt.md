# Layer 1 — prompt engineering

> Generated on this computer by the local model `llama3.1:8b` via http://127.0.0.1:11434.  
> Run: 2026-09-15 20:48

## Vague prompt

```text
Write a learning objective about hydraulic safety.
```

**Reply** (18 prompt tokens):

```text
Here is a potential learning objective about hydraulic safety:

**Learning Objective:**

Upon completion of this training, learners will be able to identify and mitigate potential hazards associated with hydraulic systems, including proper handling and maintenance procedures, and implement safe work practices to prevent injuries and damage to equipment.

**Specifically, learners will be able to:**

* Recognize the hazards associated with hydraulic systems, including pressure, fluid leaks, and entanglements
* Identify proper personal protective equipment (PPE) and safety gear for working with hydraulic systems
* Describe safe handling and maintenance procedures for hydraulic equipment, including inspection, testing, and repair
* Apply safe work practices to prevent injuries and damage to equipment, including lockout/tagout procedures and emergency shutdown protocols.

This learning objective is specific, measurable, achievable, relevant, and time-bound (SMART), and can be used as a guide for developing a training program on hydraulic safety.
```

**Checked afterwards:** Not usable: it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate).

## Specific prompt

```text
Write one learning objective for an apprentice mechanics module on hydraulic system safety. Start with an action verb, use at most 20 words, and write exactly one sentence. Reply with the sentence only.
```

**Reply** (49 prompt tokens):

```text
Identify and explain the key hazards associated with hydraulic system operation and maintenance procedures.
```

**Checked afterwards:** Usable: passes all three house rules.

Nothing in this layer checked the answers before you saw them. The model has already forgotten both calls.

# Layer 1 — prompt engineering

> Generated on this computer by the local model `llama3.1:8b` via http://127.0.0.1:11434.  
> Run: 2026-09-15 20:45

## Vague prompt

```text
Write a learning objective about hydraulic safety.
```

**Reply** (18 prompt tokens):

```text
Here is a sample learning objective about hydraulic safety:

**Learning Objective:**

Upon completion of this training, the learner will be able to identify and mitigate potential hazards associated with hydraulic systems, including proper lockout/tagout procedures, safe system operation, and emergency shutdown protocols, in order to prevent injuries and fatalities.

**Key Performance Indicators:**

* Identify at least three common hydraulic system hazards and their potential consequences
* Describe the proper procedures for lockout/tagout of hydraulic systems
* Explain the importance of regular system maintenance and inspection in preventing hydraulic-related accidents
* Demonstrate an understanding of emergency shutdown procedures and protocols in the event of a hydraulic system failure or malfunction.
```

**Checked afterwards:** Not usable: it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate).

## Specific prompt

```text
Write one learning objective for an apprentice mechanics module on hydraulic system safety. Start with an action verb, use at most 20 words, and write exactly one sentence. Reply with the sentence only.
```

**Reply** (49 prompt tokens):

```text
Identify and assess potential hazards associated with hydraulic systems to prevent accidents and injuries.
```

**Checked afterwards:** Usable: passes all three house rules.

Nothing in this layer checked the answers before you saw them. The model has already forgotten both calls.

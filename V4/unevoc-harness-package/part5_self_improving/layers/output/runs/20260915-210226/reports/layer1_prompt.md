# Layer 1 — prompt engineering

> Generated on this computer by the local model `llama3.1:8b` via http://127.0.0.1:11434.  
> Run: 2026-09-15 21:02

## Vague prompt

```text
Write a learning objective about hydraulic safety.
```

**Reply** (18 prompt tokens):

```text
Here is a sample learning objective about hydraulic safety:

**Learning Objective:**

Upon completion of this training, the learner will be able to identify and mitigate potential hazards associated with hydraulic systems, including proper operation, maintenance, and emergency procedures, in order to prevent accidents and ensure a safe working environment.

**Specifically, the learner will be able to:**

* Identify potential hazards associated with hydraulic systems, including fluid leaks, pressure surges, and equipment malfunctions
* Describe proper procedures for operating and maintaining hydraulic equipment, including pre-use checks and post-use shutdown procedures
* Explain emergency procedures for responding to hydraulic system failures or accidents, including evacuation procedures and first aid techniques
* Recognize the importance of personal protective equipment (PPE) and proper attire when working with hydraulic systems
* Apply knowledge of hydraulic safety principles to prevent accidents and ensure a safe working environment.
```

**Checked afterwards:** Not usable: it started with 'here', which is not one of the allowed action verbs (identify, describe, explain, demonstrate, apply, analyse, analyze, evaluate).

## Specific prompt

```text
Write one learning objective for an apprentice mechanics module on hydraulic system safety. Start with an action verb, use at most 20 words, and write exactly one sentence. Reply with the sentence only.
```

**Reply** (49 prompt tokens):

```text
Identify and assess potential hazards associated with hydraulic system operation and maintenance procedures to ensure safe working practices.
```

**Checked afterwards:** Usable: passes all three house rules.

Nothing in this layer checked the answers before you saw them. The model has already forgotten both calls.

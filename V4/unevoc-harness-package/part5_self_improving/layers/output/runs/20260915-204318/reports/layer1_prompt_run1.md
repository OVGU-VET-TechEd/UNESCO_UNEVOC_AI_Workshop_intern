# Layer 1 — prompt engineering

> Generated on this computer by the local model `llama3.1:8b` via http://127.0.0.1:11434.  
> Run: 2026-09-15 20:44

## Vague prompt

```text
Write a learning objective about hydraulic safety.
```

**Reply** (18 prompt tokens):

```text
Here is a sample learning objective about hydraulic safety:

**Learning Objective:**

Upon completion of this training, the learner will be able to identify and mitigate potential hazards associated with hydraulic systems, including proper maintenance, inspection, and operation procedures, in order to prevent accidents and ensure a safe working environment.

**Specifically, the learner will be able to:**

* Identify potential hazards associated with hydraulic systems, including fluid leaks, equipment malfunctions, and operator error
* Describe proper maintenance and inspection procedures for hydraulic equipment, including fluid checks and filter replacements
* Explain safe operating procedures for hydraulic equipment, including proper use of personal protective equipment (PPE) and adherence to manufacturer guidelines
* Develop a plan to respond to hydraulic system emergencies, including fluid spills and equipment malfunctions

**Assessment will be based on the learner's ability to demonstrate knowledge and application of hydraulic safety principles in a practical scenario.**
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

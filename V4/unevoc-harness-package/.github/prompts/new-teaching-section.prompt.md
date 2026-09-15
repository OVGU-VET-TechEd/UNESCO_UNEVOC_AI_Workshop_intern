---
name: new-teaching-section
description: Draft a new teaching section to this package's editorial standard.
agent: Author
argument-hint: which file, and what the section should cover
tools: ['edit', 'web/fetch', 'search/codebase', 'runCommands']
---

Draft: ${input:brief:which file, and what the section should cover}

Before writing:

1. Read the neighbouring sections in the target file. Match their level and sequencing — this
   package is ordered, not a collection.
2. If the section touches an external source, **re-open it** with #tool:web/fetch. Do not
   paraphrase from memory. The four project sources are Learn Harness Engineering, the
   Meta-Harness paper, and the two UNESCO AI competency frameworks (2024).

While writing:

- UNESCO levels are Acquire / Deepen / Create (teachers), Understand / Apply / Create (students).
- LiaScript: `[( )]` / `[(X)]` single choice, `[[ ]]` / `[[X]]` multiple choice, `--{{n}}--`
  speaker notes under every slide.
- If a claim cannot be confirmed, write that it could not be confirmed. Do not invent a date, a
  figure or a framework term.
- End with a one-paragraph UNESCO mapping. One paragraph.
- No marketing language, no generic disclaimers.

After writing:

- Run `make verify` and paste the output.
- State which sources you re-read.

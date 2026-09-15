---
applyTo: "part1_timeline/**/*.md,part2_teaching/**/*.md,part3_worked_example/**/*.md,part4_unesco_brief/**/*.md"
description: Editorial rules for anything a UNEVOC facilitator will teach from.
---

# Teaching content rules

## Accuracy

- Every factual claim traces to one of the four project sources: Learn Harness Engineering,
  the Meta-Harness paper, and the two UNESCO AI competency frameworks (2024).
- Short attributed phrases only. Do not reproduce source text.
- **UNESCO terminology is fixed**: Acquire / Deepen / Create (teachers); Understand / Apply /
  Create (students). Fifteen competencies across five aspects; twelve across four dimensions.
  "AI-literate" and "AI-enhanced educator" are not UNESCO's words.
- When something cannot be confirmed, write that it could not be confirmed. An explicit gap is a
  correct output; a plausible invention is a defect that survives into a classroom.
- Dated claims ("no revised edition as of July 2026") must carry their date so a reader knows to
  re-check.

## Structure

- Every teaching artefact ends with a **one-paragraph** UNESCO framework mapping. One paragraph.
- LiaScript decks: `#`/`##`/`###` slides, `{{n}}` fragment reveals, `--{{n}}--` speaker notes
  under **every** slide, a quiz closing every section. Single choice `[( )]` / `[(X)]`;
  multiple choice `[[ ]]` / `[[X]]`.
- Runbooks: numbered steps, each ending in a `✅ check` line stating exactly what success looks
  like. A troubleshooting note only where a step is genuinely fragile.

## Voice

- No marketing language. No generic AI-safety disclaimers. The audience is technical and academic.
- State limitations plainly and in place, not in a footnote.
- Prefer a table to three paragraphs when the content is genuinely tabular; prefer prose when it
  is not.

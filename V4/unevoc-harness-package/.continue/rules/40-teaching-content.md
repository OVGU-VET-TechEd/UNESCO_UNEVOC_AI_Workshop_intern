---
name: Teaching content
globs: "part1_timeline/**/*.md,part2_teaching/**/*.md,part3_worked_example/**/*.md,part4_unesco_brief/**/*.md"
---

# Editorial rules

Everything here will be taught from by people who are not software engineers.

## Accuracy

- Every factual claim traces to one of four sources: Learn Harness Engineering, the Meta-Harness
  paper (Lee, Nair, Zhang, Lee, Khattab & Finn, COLM 2026), and the two UNESCO AI competency
  frameworks (2024). Short attributed phrases only; no reproduction of source text.
- **UNESCO terminology is fixed.** Acquire / Deepen / Create (teachers, 15 competencies across
  five aspects); Understand / Apply / Create (students, 12 across four dimensions).
  "AI-literate" and "AI-enhanced educator" are **not** UNESCO's words.
- If something cannot be confirmed, write that it could not be confirmed. An explicit gap is a
  correct output; a plausible invention is a defect that survives into a classroom.
- Dated claims carry their date, so a reader knows to re-check.
- Re-open sources before asserting anything about them. Do not paraphrase from memory.

## Structure

- Every artefact ends with a **one-paragraph** UNESCO framework mapping. One paragraph.
- LiaScript decks: `#`/`##`/`###` slides, `{{n}}` fragment reveals, `--{{n}}--` speaker notes
  under **every** slide, a quiz closing every section. Single choice `[( )]` / `[(X)]`; multiple
  choice `[[ ]]` / `[[X]]`. `make verify` checks this.
- Runbooks: numbered steps, each ending in a `✅ check` line stating exactly what success looks
  like. Troubleshooting notes only where a step is genuinely fragile.

## Voice

No marketing language. No generic AI-safety disclaimers. The audience is technical and academic.
State limitations plainly and in place, not in a footnote.

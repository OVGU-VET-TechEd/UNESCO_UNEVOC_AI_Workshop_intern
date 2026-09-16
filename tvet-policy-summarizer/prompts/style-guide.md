# Style guide: TVET policy summaries

This guide is authoritative for every agent, model and person producing summaries in this workspace.

## 1. Length and form
- The **Summary** section has a **maximum of 80 words** (target 60-80 words).
- Exactly one paragraph. No bullet points, no headings, no line breaks, no quotations.
- Complete sentences. No exclamation marks, no rhetorical questions.

## 2. Language and tone
- English, consistent British spelling (e.g. "programme", "organisation"), regardless of source language.
- Neutral and factual. Describe what the document says; do not evaluate, praise, criticise or recommend.
- Third person only. Never use "I", "we", "our", "you".
- Present tense for what the document does ("The strategy sets out ..."); past tense only for completed events.
- Attribute content to the document: "The document states / aims to / introduces / assigns ...".
- No speculation about impact, success or intentions beyond what is written.
- Avoid evaluative words such as: groundbreaking, landmark, ambitious, impressive, excellent,
  outstanding, remarkable, innovative-as-praise, crucial, vital, comprehensive, robust, successfully.
- Spell out abbreviations at first use, except TVET. Keep abbreviations to a minimum.
- Numbers as digits; reproduce targets, dates and figures exactly as stated.

## 3. Content of the summary (recommended order)
1. Document type, issuing body, country or region, year and scope.
2. Main objectives.
3. Key measures or instruments.
4. Target groups, governance, funding or timeframe where stated.

## 4. Metadata
- **Title**: official title as written. If not in English, add an English translation in square brackets.
- **Issuing body**, **Country / region**, **Year**, **Document type**: as stated in the document.
- Write `Not stated` if the document does not provide the information. Do not guess.

## 5. Keywords
- 3 to 5 keywords, lowercase except proper nouns, separated by semicolons.

## 6. Output template

```
# <Title>

| Field | Value |
|---|---|
| Source file | <file name>.pdf |
| Issuing body | <...> |
| Country / region | <...> |
| Year | <...> |
| Document type | <...> |

## Summary

<one neutral paragraph, maximum 80 words>

## Keywords

<keyword>; <keyword>; <keyword>

---

*Word count: <n>/80 | Generated: <YYYY-MM-DD> | Agent: <agent> | Model: <model>*
```

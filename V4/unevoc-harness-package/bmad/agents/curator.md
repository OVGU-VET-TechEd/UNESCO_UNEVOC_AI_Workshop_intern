# `@curator` — corpus hygiene

**Owns:** everything between "documents arrive" and "the knowledge base is safe to index".

## Charter

Documents enter at `part4_unesco_brief/demo_assistant/corpus_raw/`. The curator moves them to
`corpus/` through the anonymiser, makes the resulting report readable, and rebuilds `kb.json`.
The curator is the only role permitted to touch the corpus pipeline.

## May write to

- `corpus_raw/` — adding, removing, renaming source documents
- `names.txt` — the explicit redaction list passed to `anonymise.py --names`
- Nothing else. `corpus/`, `kb.json` and `anonymisation_report.md` are build artefacts and are
  produced by running the tools, never by editing.

## Procedure

1. Place or update documents in `corpus_raw/`.
2. Run `make corpus`.
3. **Stop.** Present `anonymisation_report.md` to the human and wait. This is a hard checkpoint,
   not a formality — see the stop conditions below.
4. Once the human confirms, run `make kb`.
5. Run `make verify` and paste the output.

## Stop conditions — the curator must halt and ask a human

- After every anonymisation run, before indexing. Always.
- When a document is a PDF: `anonymise.py` copies PDFs through unchanged and flags them. A PDF
  must be confirmed already-public or converted to text and re-scrubbed. Never index an
  unscrubbed PDF.
- When `anonymisation_report.md` reports "no direct identifiers found" for a document that
  plainly discusses individuals. That is a signal the scrubber missed something, not a clean bill.
- When asked to index anything whose clearance is unknown.

## What the curator must never claim

That a document is anonymised. The tool removes identifiers with a predictable shape. It cannot
find names it was not given and cannot detect indirect identifiers at all — "the only welding
instructor at partner C" names a person and contains no name. The curator reports **what was
removed**, and leaves the judgement to the human.

## Definition of done

`make verify` exits 0, its `anonymisation` and `knowledgebase` checks both pass, and the human
has confirmed the report.

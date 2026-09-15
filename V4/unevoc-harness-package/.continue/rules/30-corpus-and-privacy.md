---
name: Corpus and privacy
globs: "part4_unesco_brief/demo_assistant/**"
---

# The corpus pipeline

```
corpus_raw/   what you were given          ← the ONLY folder you may edit
     ↓  anonymise.py
corpus/       cleared, ready to index      ← build artefact, never edit
     ↓  kb_build.py
kb.json       the knowledge base           ← build artefact, never edit
```

Editing `corpus/`, `kb.json` or `anonymisation_report.md` by hand desynchronises the corpus from
the index and `make verify` will fail with a `knowledgebase` error. To change what is in them:
edit `corpus_raw/`, `make corpus`, **a human reads the report**, `make kb`.

## The human checkpoint is not optional

Never index a corpus before a person has read `anonymisation_report.md`. Not for small changes,
not for releases, not when you are confident. Stop and ask.

## Never claim a document is anonymised

`anonymise.py` finds identifiers with a predictable shape — emails, phone numbers, IBANs,
handles, titled names. It **cannot**:

- find names it was not given (`--names names.txt` is the reliable path);
- detect indirect identifiers at all — "the only welding instructor at partner C" names a person
  and contains no name;
- judge sensitivity — a fully de-identified document can still be one you may not circulate.

PDFs are copied through **unchanged** and flagged. Never index an unscrubbed PDF.

Report what was removed. Leave the judgement to the human.

## The demo corpus is synthetic

The eight documents in `corpus_raw/` were invented for this package. They are not UNESCO or
UNEVOC material. If they are replaced with real documents for a pilot, the result is internal and
must not be circulated.

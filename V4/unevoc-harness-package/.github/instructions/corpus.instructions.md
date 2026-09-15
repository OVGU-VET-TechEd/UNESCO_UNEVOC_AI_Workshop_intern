---
applyTo: "part4_unesco_brief/demo_assistant/corpus/**,part4_unesco_brief/demo_assistant/kb.json,part4_unesco_brief/demo_assistant/anonymisation_report.md"
description: These are build artefacts. Do not edit them.
---

# These files are generated. Do not edit them.

`corpus/`, `kb.json` and `anonymisation_report.md` are produced by `anonymise.py` and
`kb_build.py`. Editing them by hand desynchronises the corpus from the knowledge base, and
`make verify` will fail with a `knowledgebase` error.

To change what is in them:

1. Edit `corpus_raw/`.
2. `make corpus`.
3. **A human reads `anonymisation_report.md`.** This step is not optional and cannot be performed
   by an agent.
4. `make kb`.

If asked to "just fix" something in `corpus/`, decline and explain this pipeline instead.

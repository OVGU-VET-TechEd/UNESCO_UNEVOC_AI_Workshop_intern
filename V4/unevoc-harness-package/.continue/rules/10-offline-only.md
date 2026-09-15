---
name: Offline only
alwaysApply: true
---

# Offline only — this is enforced, not aspirational

The only permitted network endpoint anywhere in this repository is `http://127.0.0.1:11434`
(Ollama), read from `OLLAMA_URL` with that default.

`make verify` scans every non-comment line of every `.py` file for URLs and **fails the build** on
anything else. Do not add a cloud SDK, an API client, a CDN link in HTML, or a web font.

Three separate reasons, often collapsed into one:

1. **Data protection** — draft policy and unpublished project data never leave the institution.
2. **Reproducibility** — a pinned local model gives the same answer next year; a hosted model is
   updated underneath you, which is fatal for a published methodology.
3. **Cost predictability** — the cost is the hardware, known in advance.

Related: `report.html` and `FILE_B_cheatsheet.html` are single self-contained files. Charts are
embedded base64 PNGs and all CSS is inline. They must open on a machine with no network.

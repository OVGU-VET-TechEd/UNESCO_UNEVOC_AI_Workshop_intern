---
name: release
description: Run workflow W3 — release. Starts with QA, ends with a verified archive.
agent: UNEVOC Lead
---

Run workflow [W3 — Release](../../bmad/workflows/W3_release.md).

1. **Author**: confirm every external claim still traces to a live source. Re-fetch; do not
   recall. Re-check the UNESCO framework pages for a revised edition — the package states that
   none was found as of July 2026, and shipping that sentence unchecked turns a cautious claim
   into a false one.
2. **QA**: `make verify`, `make demo`, full report with the limitations paragraph. Must be PASS.
3. **Packager**: clean-room rebuild — `make clean`, `make corpus`, human confirms the
   anonymisation report, `make kb`, `make verify`, `make package`. Then extract the archive
   somewhere temporary and run `make verify` there. An archive that only verifies in place has
   not been verified.
4. **Human**: confirm the shipped corpus is the synthetic one, not a local pilot corpus, and
   record that confirmation in `PROGRESS.md`.

Do not skip step 4, and do not answer it yourself.

---
name: verify
description: Run the package definition of done and report verbatim, with limitations.
agent: QA
---

Run `make verify`, then `make demo`.

Report:

1. **PASS** or **FAIL** and the exit code of `make verify`.
2. The full output, verbatim. Do not summarise it — a summarised check is not a check.
3. For every failure: the check name, the file, and which agent owns the fix
   (Curator / Librarian / Author / Packager).
4. The limitations paragraph from [`bmad/agents/qa.md`](../../bmad/agents/qa.md), stating what
   these checks do **not** cover.

Do not fix anything. You are read-only.

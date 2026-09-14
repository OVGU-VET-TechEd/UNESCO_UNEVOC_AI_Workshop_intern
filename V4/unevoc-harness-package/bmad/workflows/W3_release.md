# W3 — Release

**Use when:** distributing the package outside the project team.
**Chain:** `@author` → `@qa` → `@packager`

| # | Who | Step | Exit condition |
|---|---|---|---|
| 1 | `@author` | Confirm every external claim still traces to a live source. Re-fetch, do not recall. | Sources re-read; anything unverifiable flagged in the text |
| 2 | `@author` | Re-check the UNESCO framework pages for a revised edition | Either no change, or the mappings updated |
| 3 | `@qa` | `make verify`, `make demo`, full report with limitations | PASS |
| 4 | `@packager` | Clean-room rebuild and package (see `bmad/agents/packager.md`) | `make verify` exits 0 inside a fresh extraction |
| 5 | **human** | Confirm the shipped corpus is the synthetic one, not a local pilot corpus | Confirmed in writing in `PROGRESS.md` |

**Step 2 exists because the material makes dated claims.** The package states that no post-2024
UNESCO revision was found as of July 2026. Shipping that sentence without re-checking makes it a
false claim rather than a cautious one.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layer5_evolve.py — Layer 5: the loop writes the skill file.

    python layer5_evolve.py
    python layer5_evolve.py --model gemma3:12b --iterations 5

Runs part5_self_improving/wiki_agent.py from an empty workspace with your local
model, then collects what it wrote: the evolved SKILL.md, the wiki pattern
pages, and the skill-impact audit trail. With a real model the scores, the
number of iterations and any rollback will differ from the page's replay.
"""

from __future__ import annotations

import json
import os
import re

import layer_common as lc

WORKSPACE = os.path.join(lc.PART5, "workspace")
SKILL = os.path.join(WORKSPACE, "skills", "SKILL.md")
PATTERNS = os.path.join(WORKSPACE, "wiki", "patterns")
IMPACT = os.path.join(WORKSPACE, "wiki", "skill-impact.md")
LOGS = os.path.join(WORKSPACE, "wiki", "logs.md")
BASELINE = os.path.join(WORKSPACE, "raw", "iter00_val-baseline.json")


def outcome_data(code: int) -> dict:
    """Read the numbers back out of the files wiki_agent.py wrote."""
    baseline = None
    if os.path.exists(BASELINE):
        with open(BASELINE, "r", encoding="utf-8") as handle:
            scores = [t.get("score", 0) for t in json.load(handle)]
        baseline = round(100 * sum(scores) / len(scores)) if scores else 0

    rollouts = {}
    if os.path.exists(LOGS):
        for n, pct, passed, total in re.findall(
                r"^## Iteration (\d+) .*\n\n- Rollout score: (\d+)% \((\d+)/(\d+) passed\)",
                lc.read(LOGS), re.MULTILINE):
            rollouts[int(n)] = {"rollout_score": int(pct), "rollout_passed": int(passed),
                                "rollout_tasks": int(total)}

    iterations = []
    if os.path.exists(IMPACT):
        for n, verdict, score, previous, lines in re.findall(
                r"^## Iteration (\d+) — (ACCEPTED|ROLLED BACK)\s+- Validation score: (\d+)% "
                r"\(previous best (\d+)%\)\s+- Skill length: (\d+) lines", lc.read(IMPACT), re.MULTILINE):
            iterations.append({"iteration": int(n), "kept": verdict == "ACCEPTED",
                               "validation_score": int(score), "previous_best": int(previous),
                               "skill_lines": int(lines), **rollouts.get(int(n), {})})

    kept = [i["validation_score"] for i in iterations if i["kept"]]
    return {
        "agent_exit_code": code,
        "baseline_score": baseline,
        "final_score": max(kept) if kept else baseline,
        "iterations_run": len(rollouts),
        "kept": sum(i["kept"] for i in iterations),
        "rolled_back": sum(not i["kept"] for i in iterations),
        "iterations": iterations,
        "pattern_pages": sorted(os.listdir(PATTERNS)) if os.path.isdir(PATTERNS) else [],
        # Contents too, so the record survives workspace/ being overwritten by a later run.
        "pattern_texts": {name: lc.read(os.path.join(PATTERNS, name))
                          for name in sorted(os.listdir(PATTERNS))} if os.path.isdir(PATTERNS) else {},
        "impact": lc.read(IMPACT) if os.path.exists(IMPACT) else None,
        "skill": lc.read(SKILL) if os.path.exists(SKILL) else None,
    }


def main() -> int:
    args = lc.parse_args(__doc__.splitlines()[1],
                         lambda p: p.add_argument("--iterations", type=int, default=5))
    lc.require_model(args.model)

    code = lc.run_script(["wiki_agent.py", "--model", args.model, "--reset",
                          "--iterations", str(args.iterations)], cwd=lc.PART5)

    parts = [f"`wiki_agent.py --model {args.model} --reset --iterations {args.iterations}` "
             f"exited with code {code}."]
    if os.path.exists(SKILL):
        parts.append(f"## The skill it wrote for itself\n\n{lc.fence(lc.read(SKILL))}")
    else:
        parts.append("## The skill it wrote for itself\n\nNo SKILL.md was kept.")
    if os.path.isdir(PATTERNS):
        for name in sorted(os.listdir(PATTERNS)):
            parts.append(f"## wiki/patterns/{name}\n\n{lc.fence(lc.read(os.path.join(PATTERNS, name)))}")
    if os.path.exists(IMPACT):
        parts.append(f"## wiki/skill-impact.md\n\n{lc.fence(lc.read(IMPACT))}")

    lc.write_report("layer5_evolve.md", "Layer 5 — self-improving agent", args.model,
                    "\n\n".join(parts))
    lc.write_data("layer5_evolve", args.model, outcome_data(code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

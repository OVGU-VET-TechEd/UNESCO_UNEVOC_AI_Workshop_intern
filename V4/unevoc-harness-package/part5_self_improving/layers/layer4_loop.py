#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layer4_loop.py — Layer 4: the model proposes, the harness disposes.

    python layer4_loop.py
    python layer4_loop.py --model mistral-small3.1:24b

Runs part3_worked_example/agent.py from scratch with your local model on the
three sample PDFs, then shows the agent_log.md it wrote — the real version of
the page's "Run the agent" replay. Needs the Part 3 dependencies (run
run_package.py once, or pip install -r part3_worked_example/requirements.txt).
"""

from __future__ import annotations

import json
import os
import re

import layer_common as lc

PART3 = os.path.join(lc.ROOT, "part3_worked_example")
OUT = os.path.join(PART3, "output_agent")
LOG = os.path.join(OUT, "agent_log.md")
STATE = os.path.join(OUT, "state.json")


def main() -> int:
    args = lc.parse_args(__doc__.splitlines()[1])
    lc.require_model(args.model)

    if not any(f.endswith(".pdf") for f in os.listdir(os.path.join(PART3, "input_pdfs"))):
        lc.run_script(["make_sample_pdfs.py"], cwd=PART3)
    code = lc.run_script(["agent.py", "--model", args.model, "--reset"], cwd=PART3)

    if not os.path.exists(LOG):
        print("agent.py wrote no log; see the error above.")
        lc.write_data("layer4_loop", args.model, {"agent_exit_code": code, "log_missing": True})
        return code or 1
    log = lc.read(LOG)
    state = {}
    if os.path.exists(STATE):
        with open(STATE, "r", encoding="utf-8") as handle:
            state = json.load(handle)

    overrides = len(re.findall(r"I overrode the proposal", log))
    print(f"\n{'=' * 70}\n{log}\n{'=' * 70}")
    print(f"agent.py exit code {code}; the harness overrode the model {overrides} time(s).")

    body = (f"`agent.py --model {args.model} --reset` exited with code {code}.\n\n"
            f"Proposals the harness overrode: **{overrides}**. Every one is a place where the "
            f"model proposed something the harness did not allow.\n\n"
            f"Full log (`{os.path.relpath(LOG, lc.ROOT)}`):\n\n---\n\n{log}")
    lc.write_report("layer4_loop.md", "Layer 4 — loop engineering: agent.py", args.model, body)
    lc.write_data("layer4_loop", args.model, {
        "agent_exit_code": code,
        "steps": len(re.findall(r"^## Step \d+", log, re.MULTILINE)),
        "overrides": overrides,
        # Two wordings in agent.py: "...it is not, because X." and "`x` is not one of my five tools."
        "override_reasons": re.findall(
            r"^\s*(?:I checked whether that is allowed right now: it is not, because )?"
            r"(.+?)\.\s+\*\*I overrode the proposal\*\*", log, re.MULTILINE),
        "stop_condition_met": "stop condition is met" in log,
        "hit_step_limit": "hard limit" in log,
        "model_recorded_in_state": state.get("model"),
        "pdfs": len(state.get("pdfs", [])),
        "summaries": {name: entry.get("summary", "")
                      for name, entry in state.get("summarised", {}).items()},
        "report_written": os.path.exists(os.path.join(OUT, "report.md")),
    })
    return code


if __name__ == "__main__":
    raise SystemExit(main())

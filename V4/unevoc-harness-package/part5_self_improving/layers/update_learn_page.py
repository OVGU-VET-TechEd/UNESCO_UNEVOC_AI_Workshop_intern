#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_learn_page.py — put a real lab run into LEARN_the_five_layers.html.

    python update_learn_page.py                                  # newest run in output/runs/
    python update_learn_page.py --run output/runs/20260915-210226
    python update_learn_page.py --html ../../../LEARN_the_five_layers.html   # another copy

Reads outcomes.json and the lab logs of one run_all_layers.py run and rewrites
the block between REAL-DATA-BEGIN and REAL-DATA-END in the page. The page still
never calls a model: it shows what the model did in that run, and says which
model and when. Runs made with the mock server are refused unless --allow-mock.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import re
import sys

import layer_common as lc

PAGE = os.path.join(lc.PART5, "LEARN_the_five_layers.html")
WORKSPACE = os.path.join(lc.PART5, "workspace")
BLOCK = re.compile(r"/\* REAL-DATA-BEGIN.*?/\* REAL-DATA-END \*/", re.DOTALL)
HEADER = ("/* REAL-DATA-BEGIN — written by part5_self_improving/layers/update_learn_page.py; "
          "do not edit by hand. */")


def latest_run() -> str:
    base = os.path.join(lc.OUTPUT, "runs")
    runs = sorted(d for d in os.listdir(base)
                  if os.path.exists(os.path.join(base, d, "outcomes.json"))) if os.path.isdir(base) else []
    if not runs:
        sys.exit("No run found in output/runs/. Run run_all_layers.py first.")
    return os.path.join(base, runs[-1])


def last(lab: dict | None) -> tuple[dict | None, dict | None]:
    """The data and run record of the lab's last finished run."""
    for run in reversed((lab or {}).get("runs", [])):
        if run["data"] is not None:
            return run["data"], run
    return None, None


def e(text: str) -> str:
    return html.escape(text, quote=False)


def loop_lines(log_text: str, data: dict) -> list[list[str]] | None:
    """agent_log.md, as embedded in the lab 4 console log, turned into replay lines."""
    start = log_text.rfind("# Agent run")
    if start < 0:
        return None
    lines: list[list[str]] = []
    for raw in log_text[start:].split("\n=====")[0].splitlines():
        s = raw.strip().replace("**", "").replace("`", "")
        if not s or s == "---" or s.startswith(("# Agent run", "Everything below", "Final state")):
            continue
        step = re.match(r"## Step (\d+)", s)
        if s.startswith(("Model used", "The rule I follow")):
            lines.append(["dim", s])
        elif step:
            lines.append(["hi", f"Step {step.group(1)}"])
        elif "I overrode the proposal" in s:
            lines.append(["bad", "  OVERRIDE. " + s])
        elif s.startswith("I verified"):
            lines.append(["ok", "  " + s])
        elif s.startswith("Stopping."):
            lines += [["hi", "Stopping."], ["ok", "  " + s[len("Stopping."):].strip()]]
        else:
            lines.append(["", ("  " + s) if s.startswith("I ") else s])
    lines.append(["dim", f"\n{data['overrides']} override(s) in {data['steps']} steps. "
                         f"Nobody typed anything."])
    return [[cls, e(text)] for cls, text in lines]


def evo_lines(log_text: str) -> list[list[str]] | None:
    """The wiki_agent.py console output of lab 5, turned into replay lines."""
    start = log_text.find("Baseline with no skill at all")
    end = log_text.find("The model never changed")
    if start < 0 or end < 0:
        return None
    lines = []
    for raw in log_text[start:end].splitlines():
        text = raw.strip()
        if not text or set(text) == {"="}:
            continue
        if text.startswith(("Baseline with no skill", "(the wiki", "Validation is perfect")):
            cls = "dim"
        elif text.startswith(("ITERATION", "Baseline ")):
            cls = "hi"
        elif "-> KEPT" in text:
            cls = "ok"
        elif "ROLLED BACK" in text:
            cls = "bad"
        else:
            cls = ""
        lines.append([cls, e(raw.rstrip())])
    lines.append(["dim", "The model never changed. Only the text around it did."])
    return lines


def workspace_from_run(env: dict) -> bool:
    """True if workspace/ still holds the files of this run (run_package.py overwrites it)."""
    baseline = os.path.join(WORKSPACE, "raw", "iter00_val-baseline.json")
    if not os.path.exists(baseline):
        return False
    started = _dt.datetime.fromisoformat(env["started"]).timestamp()
    finished = _dt.datetime.fromisoformat(env["finished"]).timestamp()
    return started - 5 <= os.path.getmtime(baseline) <= finished + 5


def build(run_dir: str) -> dict:
    with open(os.path.join(run_dir, "outcomes.json"), "r", encoding="utf-8") as handle:
        outcomes = json.load(handle)
    env = outcomes["environment"]
    labs = {lab["id"]: lab for lab in outcomes["labs"]}
    details = env.get("model_details", {})

    def log_of(run: dict | None) -> str:
        path = os.path.join(run_dir, run["log"]) if run else ""
        return lc.read(path) if run and os.path.exists(path) else ""

    real: dict = {
        "run": os.path.basename(os.path.normpath(run_dir)),
        "model": env["model"],
        "date": env["started"].replace("T", " ")[:16],
        "modelInfo": " ".join(x for x in (details.get("parameter_size"),
                                          details.get("quantization_level")) if x) or "details unknown",
        "ollama": env.get("ollama_version") or "unknown",
    }

    data, _ = last(labs.get("0"))
    real["lab0"] = data["samples"] if data else None

    for lab_id, key, names in (("1", "kind", {"vague": "vague", "specific": "specific"}),
                               ("2", "variant", {"without skill": "without", "with skill": "with"})):
        data, _ = last(labs.get(lab_id))
        real[f"lab{lab_id}"] = {"results": [
            {"variant": names[r[key]], "answer": r["answer"], "passed": r["passed"],
             "reason": r["reason"], "words": r["words"], "prompt_tokens": r["prompt_tokens"],
             "answer_tokens": r["answer_tokens"], "seconds": r["seconds"]}
            for r in data["results"]]} if data else None

    for lab_id in ("3", "3b"):
        data, _ = last(labs.get(lab_id))
        real[f"lab{lab_id}"] = {"ok": data["checks_ok"], "failures": data["failures"],
                                "exit": data["verify_exit_code"]} if data else None

    data, run = last(labs.get("4"))
    lines = loop_lines(log_of(run), data) if data and not data.get("log_missing") else None
    real["lab4"] = {"lines": lines, "steps": data["steps"], "overrides": data["overrides"]} if lines else None

    data, run = last(labs.get("5"))
    lines = evo_lines(log_of(run)) if data else None
    if data and lines:
        patterns, impact = data.get("pattern_texts"), data.get("impact")
        if patterns is None and workspace_from_run(env):
            folder = os.path.join(WORKSPACE, "wiki", "patterns")
            patterns = {n: lc.read(os.path.join(folder, n)) for n in data["pattern_pages"]
                        if os.path.exists(os.path.join(folder, n))}
            path = os.path.join(WORKSPACE, "wiki", "skill-impact.md")
            impact = lc.read(path) if os.path.exists(path) else None
        names = [n for n in (patterns or {}) if n != "what-works.md"] or list(patterns or {})
        kept = [i["iteration"] for i in data["iterations"] if i["kept"]]
        real["lab5"] = {
            "lines": lines, "baseline": data["baseline_score"], "final": data["final_score"],
            "skill": data["skill"],
            "skillSource": f"iteration {kept[-1]}" if kept else "no iteration kept",
            "patternCount": len(data["pattern_pages"]),
            "patternName": names[0] if names else None,
            "pattern": patterns[names[0]] if names else None,
            "impact": impact,
        }
    else:
        real["lab5"] = None
    return real


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed a real lab run in LEARN_the_five_layers.html.")
    parser.add_argument("--run", help="run folder (default: newest in output/runs/)")
    parser.add_argument("--html", action="append", help=f"page(s) to update (default: {PAGE})")
    parser.add_argument("--allow-mock", action="store_true", help="accept a run made with mock:*")
    args = parser.parse_args()

    run_dir = args.run or latest_run()
    real = build(run_dir)
    if real["model"].startswith("mock:") and not args.allow_mock:
        sys.exit(f"{run_dir} was made with {real['model']} (canned output). Refusing to present "
                 f"it as a real run; pass --allow-mock to override.")

    blob = json.dumps(real, ensure_ascii=False, indent=1).replace("</", "<\\/")
    block = f"{HEADER}\nconst REAL = {blob};\n/* REAL-DATA-END */"

    failed = False
    for page in args.html or [PAGE]:
        text = lc.read(page)
        if not BLOCK.search(text):
            print(f"SKIP {page}: no REAL-DATA block — this copy of the page has not been prepared.")
            failed = True
            continue
        with open(page, "w", encoding="utf-8") as handle:
            handle.write(BLOCK.sub(lambda _match: block, text, count=1))
        print(f"updated {os.path.relpath(page, lc.ROOT)}")

    print(f"\nRun {real['run']} — {real['model']} ({real['modelInfo']}), {real['date']}")
    for lab_id in ("lab0", "lab1", "lab2", "lab3", "lab3b", "lab4", "lab5"):
        print(f"  {'embedded' if real.get(lab_id) else 'MISSING '}  {lab_id}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

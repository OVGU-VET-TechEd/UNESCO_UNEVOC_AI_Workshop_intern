#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all_layers.py — run every lab on its own, then report what really happened.

    python run_all_layers.py                         # all labs, llama3.1:8b
    python run_all_layers.py --model gemma3:12b
    python run_all_layers.py --labs 1,2 --repeat 5   # how stable are layers 1 and 2?

Each lab (layer0 ... layer5, plus layer 3 with a planted leak) is started as its
own process, exactly as if you had typed its command. Nothing is replayed: every
number in the outcome report is read from the JSON the lab wrote during THIS run,
and data older than the run is refused.

Output, in output/runs/<timestamp>/:
    outcomes.json   everything, machine-readable
    outcomes.md     summary table and per-lab results, for people
    logs/           the full console output of every lab run
    data/ reports/  each lab's own JSON and Markdown report, per run

Exit code 0 only if every lab finished and behaved as the page claims it should.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import shutil
import subprocess
import sys
import time

import layer_common as lc

# Model calls in layers 1 and 2 vary from run to run, so only those are repeated.
REPEATABLE = {"1", "2"}


def labs(iterations: int) -> list[dict]:
    return [
        {"id": "0", "title": "Tokens", "script": "layer0_tokens.py", "args": [],
         "name": "layer0_tokens"},
        {"id": "1", "title": "Prompt: vague vs. specific", "script": "layer1_prompt.py",
         "args": [], "name": "layer1_prompt"},
        {"id": "2", "title": "Skill: without vs. with SKILL.md", "script": "layer2_skill.py",
         "args": [], "name": "layer2_skill"},
        {"id": "3", "title": "Harness: make verify", "script": "layer3_harness.py",
         "args": [], "name": "layer3_harness"},
        {"id": "3b", "title": "Harness: verify with a planted leak", "script": "layer3_harness.py",
         "args": ["--break"], "name": "layer3_harness_break"},
        {"id": "4", "title": "Loop: agent.py", "script": "layer4_loop.py", "args": [],
         "name": "layer4_loop"},
        {"id": "5", "title": "Self-improving: wiki_agent.py", "script": "layer5_evolve.py",
         "args": ["--iterations", str(iterations)], "name": "layer5_evolve"},
    ]


def run_lab(lab: dict, model: str, run_dir: str, attempt: int, repeats: int) -> dict:
    suffix = f"_run{attempt}" if repeats > 1 else ""
    command = [sys.executable, "-u", os.path.join(lc.HERE, lab["script"]),
               "--model", model, *lab["args"]]
    log_path = os.path.join(run_dir, "logs", f"{lab['name']}{suffix}.log")
    started = time.time()

    with open(log_path, "w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=lc.HERE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True,
                                   encoding="utf-8", errors="replace")
        for line in process.stdout:
            sys.stdout.write(line)
            log.write(line)
        code = process.wait()
    seconds = round(time.time() - started, 1)

    # Only accept files this run wrote. A leftover from an earlier run is not evidence.
    data = None
    source = os.path.join(lc.OUTPUT, f"{lab['name']}.json")
    if os.path.exists(source) and os.path.getmtime(source) >= started:
        with open(source, "r", encoding="utf-8") as handle:
            record = json.load(handle)
        data = record["data"]
        shutil.copy(source, os.path.join(run_dir, "data", f"{lab['name']}{suffix}.json"))
    report = os.path.join(lc.OUTPUT, f"{lab['name']}.md")
    if os.path.exists(report) and os.path.getmtime(report) >= started:
        shutil.copy(report, os.path.join(run_dir, "reports", f"{lab['name']}{suffix}.md"))

    return {"attempt": attempt, "exit_code": code, "seconds": seconds,
            "log": os.path.relpath(log_path, run_dir), "data": data}


def pass_counts(runs: list[dict], key: str) -> dict[str, list[int]]:
    counts: dict[str, list[int]] = {}
    for run in runs:
        for result in (run["data"] or {}).get("results", []):
            entry = counts.setdefault(result[key], [0, 0])
            entry[0] += int(result["passed"])
            entry[1] += 1
    return counts


def assess(lab: dict, runs: list[dict], model: str) -> tuple[bool, str]:
    """Did the lab show what the page says it shows? Returns (as_expected, outcome)."""
    finished = [r for r in runs if r["data"] is not None]
    if not finished:
        return False, "no outcome data — the lab did not finish; see its log"
    crashed = [r for r in runs if r["exit_code"] != 0]
    d = finished[-1]["data"]
    lab_id = lab["id"]

    if lab_id == "0":
        text = "; ".join(f"{s['language']} {s['real_tokens']} tokens "
                         f"({s['tokens_per_word']}/word, page est. {s['page_estimate']})"
                         for s in d["samples"])
        return not crashed, text

    if lab_id in ("1", "2"):
        key, first, second = (("kind", "vague", "specific") if lab_id == "1"
                              else ("variant", "without skill", "with skill"))
        counts = pass_counts(finished, key)
        rate = {k: p / n for k, (p, n) in counts.items() if n}
        text = "; ".join(f"{k}: passed {p}/{n}" for k, (p, n) in counts.items())
        expected = rate.get(second, 0) > 0 and rate.get(second, 0) >= rate.get(first, 0)
        return expected and not crashed, text

    if lab_id == "3":
        text = (f"verify exit {d['verify_exit_code']}: {len(d['checks_ok'])} ok line(s), "
                f"{len(d['failures'])} failure(s)")
        if d["adapters_missing"]:
            text += " — .github/.continue/.vscode missing"
        return d["verify_exit_code"] == 0, text

    if lab_id == "3b":
        caught = [f for f in d["failures"] if f.startswith("[anonymisation]")]
        text = (f"planted email {'caught' if caught else 'NOT caught'} "
                f"(verify exit {d['verify_exit_code']}); corpus restored: {d['corpus_restored']}")
        return bool(caught) and d["verify_exit_code"] != 0 and d["corpus_restored"], text

    if lab_id == "4":
        if d.get("log_missing"):
            return False, f"agent.py wrote no log (exit {d['agent_exit_code']})"
        text = (f"{d['steps']} steps, {d['overrides']} override(s), stop condition "
                f"{'met' if d['stop_condition_met'] else 'NOT met'}"
                f"{', hit the step limit' if d['hit_step_limit'] else ''}; "
                f"model in state.json: {d['model_recorded_in_state']}")
        expected = (d["stop_condition_met"] and not d["hit_step_limit"]
                    and d["model_recorded_in_state"] == model and d["report_written"])
        return expected, text

    if lab_id == "5":
        text = (f"baseline {d['baseline_score']}% -> final {d['final_score']}% over "
                f"{d['iterations_run']} iteration(s); {d['kept']} kept, "
                f"{d['rolled_back']} rolled back; {len(d['pattern_pages'])} wiki page(s)")
        # The page's claim is improvement, so "no worse" is not enough.
        expected = (d["agent_exit_code"] == 0 and d["baseline_score"] is not None
                    and d["final_score"] > d["baseline_score"])
        if not expected and d["kept"] == 0:
            text += " — no proposed skill beat the baseline"
        return expected, text

    return not crashed, ""


def cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def details_markdown(lab: dict, runs: list[dict]) -> str:
    finished = [r for r in runs if r["data"] is not None]
    if not finished:
        return "No data. See the log(s): " + ", ".join(f"`{r['log']}`" for r in runs)
    lab_id, d = lab["id"], finished[-1]["data"]
    lines: list[str] = []

    if lab_id == "0":
        lines += ["| Language | Words | Page estimate | Real tokens | Tokens/word |",
                  "|---|---:|---:|---:|---:|"]
        lines += [f"| {s['language']} | {s['words']} | {s['page_estimate']} | {s['real_tokens']} | "
                  f"{s['tokens_per_word']} |" for s in d["samples"]]

    elif lab_id in ("1", "2"):
        key = "kind" if lab_id == "1" else "variant"
        lines += ["| Run | Variant | Passed | Reason | Words | Prompt tok | Answer tok | Seconds | Answer |",
                  "|---:|---|---|---|---:|---:|---:|---:|---|"]
        for run in finished:
            for r in run["data"]["results"]:
                answer = r["answer"] if len(r["answer"]) <= 160 else r["answer"][:157] + "..."
                lines.append(f"| {run['attempt']} | {r[key]} | {'yes' if r['passed'] else 'no'} | "
                             f"{cell(r['reason'])} | {r['words']} | {r['prompt_tokens']} | "
                             f"{r['answer_tokens']} | {r['seconds']} | {cell(answer)} |")

    elif lab_id in ("3", "3b"):
        lines += [f"- verify exit code: **{d['verify_exit_code']}**",
                  f"- ok lines: {len(d['checks_ok'])}"]
        lines += [f"- FAIL {cell(f)}" for f in d["failures"]] or ["- no failures"]

    elif lab_id == "4" and not d.get("log_missing"):
        lines += [f"- steps: {d['steps']}", f"- overrides: {d['overrides']}",
                  f"- stop condition met: {d['stop_condition_met']}",
                  f"- hit the {40}-step limit: {d['hit_step_limit']}",
                  f"- PDFs: {d['pdfs']}, report written: {d['report_written']}"]
        lines += [f"- override reason: {cell(r)}" for r in d["override_reasons"]]
        lines += ["", "| PDF | Summary written by the model |", "|---|---|"]
        lines += [f"| {name} | {cell(text)} |" for name, text in d["summaries"].items()]

    elif lab_id == "5":
        lines += ["| Iteration | Rollout score | Validation score | Previous best | Skill lines | Gate |",
                  "|---:|---:|---:|---:|---:|---|"]
        lines += [f"| {i['iteration']} | {i.get('rollout_score', '—')}% | {i['validation_score']}% | "
                  f"{i['previous_best']}% | {i['skill_lines']} | {'KEPT' if i['kept'] else 'ROLLED BACK'} |"
                  for i in d["iterations"]]
        lines += ["", "Wiki pages: " + (", ".join(f"`{p}`" for p in d["pattern_pages"]) or "none")]
        if d["skill"]:
            lines += ["", "Final SKILL.md:", "", lc.fence(d["skill"])]
    return "\n".join(lines)


def main() -> int:
    all_ids = [lab["id"] for lab in labs(5)]
    parser = argparse.ArgumentParser(description="Run every lab individually and collect outcome data.")
    parser.add_argument("--model", default=lc.DEFAULT_MODEL,
                        help=f"Ollama model tag (default {lc.DEFAULT_MODEL})")
    parser.add_argument("--labs", default=",".join(all_ids),
                        help=f"comma-separated subset of {','.join(all_ids)}")
    parser.add_argument("--repeat", type=int, default=1,
                        help="run labs 1 and 2 this many times (their answers vary)")
    parser.add_argument("--iterations", type=int, default=5, help="iterations for lab 5")
    args = parser.parse_args()

    chosen = [s.strip() for s in args.labs.split(",") if s.strip()]
    unknown = sorted(set(chosen) - set(all_ids))
    if unknown:
        parser.error(f"unknown lab(s): {', '.join(unknown)}")
    lc.require_model(args.model)

    started_at = _dt.datetime.now()
    run_dir = os.path.join(lc.OUTPUT, "runs", started_at.strftime("%Y%m%d-%H%M%S"))
    for sub in ("logs", "data", "reports"):
        os.makedirs(os.path.join(run_dir, sub), exist_ok=True)

    environment = {
        "model": args.model,
        "model_details": lc.model_details(args.model),
        "ollama_url": lc.OLLAMA_URL,
        "ollama_version": lc.ollama_version(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "started": started_at.isoformat(timespec="seconds"),
    }

    results = []
    for lab in labs(args.iterations):
        if lab["id"] not in chosen:
            continue
        repeats = args.repeat if lab["id"] in REPEATABLE else 1
        runs = []
        for attempt in range(1, repeats + 1):
            label = f" (run {attempt}/{repeats})" if repeats > 1 else ""
            print(f"\n{'#' * 70}\n#  LAB {lab['id']} — {lab['title']}{label}\n{'#' * 70}\n", flush=True)
            runs.append(run_lab(lab, args.model, run_dir, attempt, repeats))
        expected, outcome = assess(lab, runs, args.model)
        results.append({"id": lab["id"], "title": lab["title"],
                        "command": f"python {lab['script']} --model {args.model} {' '.join(lab['args'])}".strip(),
                        "as_expected": expected, "outcome": outcome, "runs": runs})

    finished_at = _dt.datetime.now()
    environment["finished"] = finished_at.isoformat(timespec="seconds")
    environment["total_seconds"] = round((finished_at - started_at).total_seconds(), 1)

    with open(os.path.join(run_dir, "outcomes.json"), "w", encoding="utf-8") as handle:
        json.dump({"environment": environment, "labs": results}, handle, indent=2, ensure_ascii=False)

    details = environment["model_details"]
    md = [f"# Lab outcomes — {args.model}", "",
          f"> Real run on this computer. Every figure below was measured during this run; "
          f"nothing is replayed from the HTML page.", "",
          "| | |", "|---|---|",
          f"| Model | `{args.model}` ({details.get('parameter_size', '?')}, "
          f"{details.get('quantization_level', '?')}, digest {details.get('digest', '?')}) |",
          f"| Ollama | {environment['ollama_version'] or 'unknown'} at {lc.OLLAMA_URL} |",
          f"| Machine | {environment['platform']}, Python {environment['python']} |",
          f"| Run | {environment['started']} → {environment['finished']} "
          f"({environment['total_seconds']} s) |", "",
          "## Summary", "",
          "| Lab | What | Runs | Exit codes | Seconds | As expected | Outcome |",
          "|---|---|---:|---|---:|---|---|"]
    for r in results:
        md.append(f"| {r['id']} | {cell(r['title'])} | {len(r['runs'])} | "
                  f"{', '.join(str(x['exit_code']) for x in r['runs'])} | "
                  f"{sum(x['seconds'] for x in r['runs']):.1f} | "
                  f"{'yes' if r['as_expected'] else '**no**'} | {cell(r['outcome'])} |")
    md += ["", "\"As expected\" means the lab showed what the page claims: the specific prompt "
               "and the skill do at least as well as their counterparts, verify passes, the "
               "planted leak is caught, the agent stops by its stop condition, and evolution "
               "ends above its baseline. A \"no\" is a real result, not a script error: "
               "read that lab's section.", ""]
    lab_by_id = {lab["id"]: lab for lab in labs(args.iterations)}
    for r in results:
        md += [f"## Lab {r['id']} — {r['title']}", "", f"`{r['command']}`", "",
               details_markdown(lab_by_id[r["id"]], r["runs"]), "",
               "Logs: " + ", ".join(f"`{x['log']}`" for x in r["runs"]), ""]
    with open(os.path.join(run_dir, "outcomes.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(md))

    print(f"\n{'=' * 70}\n  OUTCOMES — {args.model}\n{'=' * 70}")
    for r in results:
        print(f"  {'ok  ' if r['as_expected'] else 'NO  '} lab {r['id']:3} {r['outcome']}")
    print(f"\n  {os.path.relpath(os.path.join(run_dir, 'outcomes.md'), lc.ROOT)}")
    print(f"  {os.path.relpath(os.path.join(run_dir, 'outcomes.json'), lc.ROOT)}")
    return 0 if all(r["as_expected"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

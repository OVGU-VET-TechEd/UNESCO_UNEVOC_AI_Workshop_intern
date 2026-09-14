#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wiki_agent.py — LAYER 5: an agent that writes its own skill file.

WHAT THIS IS
    A small, readable implementation of the WikiSkill idea (Tang, Rashtchian,
    Ferng, Tomkins, Juan & Vu, Google Research, arXiv:2608.27454). It runs fully
    offline against a local Ollama model.

    Layers 1-4 of this package are things a HUMAN writes: the prompt, the skill
    file, the harness, the loop. Layer 5 is the loop writing the skill file.

THE THREE FOLDERS — this separation is the whole idea
    raw/     immutable execution traces. Never edited, never deleted.
    wiki/    patterns distilled from those traces. GROWS ONLY. Never rolled back.
    skills/  the active SKILL.md. Gated: reverted if it makes things worse.

    A rejected skill is thrown away. What was learned by trying it is not.
    That asymmetry is why the wiki compounds while the skill stays short.

THE FOUR ROLES PER ITERATION
    1  Inference Agent   does the task with the current skill  -> raw/
    2  Wiki Maintainer   reads traces, writes patterns          -> wiki/
    3  Skill Proposer    reads the wiki, proposes ONE edit      -> skills/ (candidate)
    4  Gate              scores on held-out tasks; keep or roll back

    Note which of these is NOT given the wiki: the Inference Agent. That is not an
    oversight. The paper's ablation found that giving the inference agent wiki
    access during training made the final skill worse (63.7% -> 60.9% average),
    because the agent solves the task from the wiki instead of from the skill,
    and the traces stop showing what the skill needs to fix.

USAGE
    python wiki_agent.py --model llama3.1:8b
    python wiki_agent.py --model qwen2.5:7b --iterations 5
    python wiki_agent.py --model mock:demo --reset      # with tools/mock_ollama.py

READ AFTERWARDS
    workspace/wiki/patterns/*.md   what it worked out
    workspace/wiki/skill-impact.md the audit trail: every proposal, kept or rolled back
    workspace/skills/SKILL.md      the skill it ended up with. Nobody wrote this.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(HERE, "workspace")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

RAW = os.path.join(WORKSPACE, "raw")
WIKI = os.path.join(WORKSPACE, "wiki")
PATTERNS = os.path.join(WIKI, "patterns")
SKILLS = os.path.join(WORKSPACE, "skills")
SKILL_FILE = os.path.join(SKILLS, "SKILL.md")
IMPACT = os.path.join(WIKI, "skill-impact.md")
LOGS = os.path.join(WIKI, "logs.md")


# ===========================================================================
# THE TASK — writing TVET learning objectives to a house standard
# ===========================================================================
# Split into train (the agent learns from these) and validation (the gate scores
# on these). The agent never sees the validation set while learning, which is why
# a score on it means something.

TRAIN_TASKS = [
    "hydraulic system safety for apprentice mechanics",
    "reading an electrical circuit diagram",
    "workplace risk assessment in a metal workshop",
    "selecting personal protective equipment for welding",
]
VALIDATION_TASKS = [
    "calibrating a torque wrench",
    "interpreting a materials safety data sheet",
    "safe isolation of a three-phase supply",
]

ALLOWED_VERBS = [
    "identify", "describe", "explain", "demonstrate", "apply", "analyse",
    "analyze", "evaluate", "design", "calculate", "inspect", "select",
    "measure", "operate", "assess", "calibrate", "interpret", "isolate",
]
MAX_WORDS = 20


def score_one(answer: str) -> tuple[float, str]:
    """The scoring function. Deterministic, model-free, and the same rules the
    minimal harness in Part 2 uses. Returns (score in [0,1], reason).

    This is the ground truth the whole loop optimises against. If it is wrong,
    everything above it is confidently wrong too — so it is the first thing to
    check when results look strange.
    """
    text = re.sub(r"^[-*\d.)\s\"']+", "", answer.strip()).strip().strip('"')
    if not text:
        return 0.0, "empty answer"

    first = re.split(r"[\s,.:;]+", text, maxsplit=1)[0].lower()
    if first not in ALLOWED_VERBS:
        return 0.0, f"opened with '{first}', not an approved action verb"

    words = len(text.split())
    if words > MAX_WORDS:
        return 0.0, f"{words} words, limit is {MAX_WORDS}"

    if len(re.findall(r"[.!?](\s|$)", text)) > 1:
        return 0.0, "more than one sentence"
    if "\n" in text.strip():
        return 0.0, "more than one line"
    return 1.0, "ok"


# ===========================================================================
# MODEL ACCESS — the only part that is "the AI"
# ===========================================================================

def call_ollama(model: str, prompt: str, num_predict: int = 300,
                temperature: float = 0.3) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=payload,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8")).get("response", "").strip()


# ===========================================================================
# 1. INFERENCE AGENT — does the task with whatever skill currently exists
# ===========================================================================

def read_skill() -> str:
    if not os.path.exists(SKILL_FILE):
        return ""
    with open(SKILL_FILE, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def run_rollouts(model: str, tasks: list[str], iteration: int,
                 tag: str) -> list[dict]:
    """Run the task on every item and write immutable traces to raw/.

    The skill is injected into the prompt. The wiki is NOT — see the module
    docstring for why that restriction is deliberate.
    """
    skill = read_skill()
    traces: list[dict] = []

    for task in tasks:
        prompt = (
            "Write one learning objective for a vocational training module.\n\n"
            + (f"Follow this guidance exactly:\n---\n{skill}\n---\n\n" if skill else "")
            + f"Topic: {task}\n\nReply with the sentence only."
        )
        try:
            answer = call_ollama(model, prompt, num_predict=80, temperature=0.3)
        except urllib.error.URLError as error:
            raise SystemExit(f"Cannot reach Ollama at {OLLAMA_URL}: {error}")

        score, reason = score_one(answer)
        traces.append({"task": task, "answer": answer, "score": score,
                       "reason": reason, "skill_present": bool(skill)})

    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, f"iter{iteration:02d}_{tag}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(traces, handle, indent=2, ensure_ascii=False)
    return traces


def mean_score(traces: list[dict]) -> float:
    return sum(t["score"] for t in traces) / max(len(traces), 1)


# ===========================================================================
# 2. WIKI MAINTAINER — turns traces into patterns. Append-only.
# ===========================================================================

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "pattern"


def maintain_wiki(model: str, traces: list[dict], iteration: int) -> list[str]:
    """Diagnose the failures and record them as pattern pages.

    Failures are grouped by their machine-checked reason, so the same failure
    mode across four tasks becomes one pattern rather than four notes. Patterns
    are updated with new evidence when they recur, never overwritten.
    """
    os.makedirs(PATTERNS, exist_ok=True)
    failures = [t for t in traces if t["score"] < 1.0]
    successes = [t for t in traces if t["score"] >= 1.0]
    touched: list[str] = []

    grouped: dict[str, list[dict]] = {}
    for trace in failures:
        key = re.sub(r"'[^']*'", "'X'", trace["reason"])
        key = re.sub(r"\d+", "N", key)
        grouped.setdefault(key, []).append(trace)

    for reason, group in grouped.items():
        name = slugify(reason) + ".md"
        path = os.path.join(PATTERNS, name)
        example = group[0]

        prompt = (
            "You are maintaining a knowledge base for an AI agent that writes "
            "vocational learning objectives.\n\n"
            f"A check rejected {len(group)} answer(s) for this reason: {reason}\n"
            f"Example rejected answer: \"{example['answer'][:200]}\"\n\n"
            "Write ONE imperative rule, under 25 words, that would prevent this. "
            "Reply with the rule only. No preamble, no bullet, no explanation."
        )
        try:
            rule = call_ollama(model, prompt, num_predict=60, temperature=0.2)
        except Exception:  # noqa: BLE001 — a missing rule is not fatal
            rule = f"Avoid: {reason}."
        rule = rule.strip().strip('"').split("\n")[0]

        if os.path.exists(path):
            # Recurrence: append evidence, keep the original diagnosis.
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"\n- Iteration {iteration}: recurred "
                             f"{len(group)} time(s). Still unresolved.\n")
        else:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    f"# Pattern: {reason}\n\n"
                    f"**First seen:** iteration {iteration}\n\n"
                    f"**What happens:** the answer is rejected because {reason}.\n\n"
                    f"**Example:** `{example['answer'][:160]}`\n\n"
                    f"**Proposed rule:** {rule}\n\n"
                    f"## Evidence\n\n"
                    f"- Iteration {iteration}: {len(group)} occurrence(s).\n")
        touched.append(name)

    if successes and not os.path.exists(os.path.join(PATTERNS, "what-works.md")):
        with open(os.path.join(PATTERNS, "what-works.md"), "w", encoding="utf-8") as handle:
            handle.write(
                "# Pattern: answers that passed\n\n"
                "Keep these shapes. They cleared every check.\n\n"
                + "".join(f"- `{t['answer'][:140]}`\n" for t in successes[:5]))
        touched.append("what-works.md")

    with open(LOGS, "a", encoding="utf-8") as handle:
        handle.write(f"\n## Iteration {iteration} — {_dt.datetime.now():%Y-%m-%d %H:%M}\n\n"
                     f"- Rollout score: {mean_score(traces):.0%} "
                     f"({len(successes)}/{len(traces)} passed)\n"
                     f"- Failure modes seen: {len(grouped)}\n"
                     f"- Pattern pages touched: {', '.join(touched) or 'none'}\n")
    return touched


def read_wiki() -> str:
    """The whole wiki as text. The Proposer sees this; the Inference Agent does not."""
    if not os.path.isdir(PATTERNS):
        return "(empty)"
    parts = []
    for name in sorted(os.listdir(PATTERNS)):
        with open(os.path.join(PATTERNS, name), "r", encoding="utf-8") as handle:
            parts.append(f"--- {name} ---\n{handle.read().strip()}")
    if os.path.exists(IMPACT):
        with open(IMPACT, "r", encoding="utf-8") as handle:
            parts.append(f"--- skill-impact.md (what was already tried) ---\n"
                         f"{handle.read().strip()}")
    return "\n\n".join(parts) if parts else "(empty)"


# ===========================================================================
# 3. SKILL PROPOSER — reads the wiki, writes the next candidate skill
# ===========================================================================

def propose_skill(model: str) -> str:
    """Propose a replacement SKILL.md, informed by the wiki and the audit trail.

    The audit trail matters as much as the patterns: it stops the proposer
    re-proposing something that was already tried and rolled back.
    """
    prompt = (
        "You are improving a SKILL.md file used by an AI agent that writes "
        "vocational learning objectives.\n\n"
        f"Current SKILL.md:\n---\n{read_skill() or '(none yet)'}\n---\n\n"
        f"Accumulated knowledge base:\n---\n{read_wiki()}\n---\n\n"
        "Write an improved SKILL.md. Requirements:\n"
        "- At most 8 short imperative rules, as a markdown list.\n"
        "- Each rule must address a failure recorded above.\n"
        "- Do not repeat a change the impact log shows was already rolled back.\n"
        "- No preamble and no explanation. Output the file content only.\n\n"
        "SKILL.md:"
    )
    return call_ollama(model, prompt, num_predict=400, temperature=0.4).strip()


# ===========================================================================
# 4. GATE — keep the change only if held-out performance improves
# ===========================================================================

def record_impact(iteration: int, score: float, best: float, accepted: bool,
                  skill: str) -> None:
    with open(IMPACT, "a", encoding="utf-8") as handle:
        handle.write(
            f"\n## Iteration {iteration} — "
            f"{'ACCEPTED' if accepted else 'ROLLED BACK'}\n\n"
            f"- Validation score: {score:.0%} (previous best {best:.0%})\n"
            f"- Skill length: {len(skill.splitlines())} lines\n"
            f"- Outcome: {'kept' if accepted else 'reverted; do not propose this again'}\n")


# ===========================================================================
# THE EVOLUTION LOOP
# ===========================================================================

def evolve(model: str, iterations: int) -> int:
    for directory in (RAW, PATTERNS, SKILLS):
        os.makedirs(directory, exist_ok=True)

    print(f"Model: {model}   workspace: {WORKSPACE}")
    print(f"{len(TRAIN_TASKS)} training tasks, {len(VALIDATION_TASKS)} validation tasks\n")

    baseline = mean_score(run_rollouts(model, VALIDATION_TASKS, 0, "val-baseline"))
    best = baseline
    print(f"Baseline with no skill at all: {baseline:.0%}\n")

    for iteration in range(1, iterations + 1):
        print(f"{'=' * 62}\nITERATION {iteration}\n{'=' * 62}")

        # 1. the agent works, with whatever skill it currently has
        traces = run_rollouts(model, TRAIN_TASKS, iteration, "train")
        print(f"  1. rollouts        {mean_score(traces):.0%} on training tasks")

        # 2. what was learned goes into the wiki, permanently
        touched = maintain_wiki(model, traces, iteration)
        print(f"  2. wiki maintainer {len(touched)} pattern page(s) written or updated")

        # 3. propose one new skill from the accumulated wiki
        candidate = propose_skill(model)
        if not candidate:
            print("  3. proposer        produced nothing; skipping this iteration")
            continue
        print(f"  3. proposer        candidate skill, {len(candidate.splitlines())} lines")

        # 4. gate it on tasks it has never seen
        previous = read_skill()
        with open(SKILL_FILE, "w", encoding="utf-8") as handle:
            handle.write(candidate)
        score = mean_score(run_rollouts(model, VALIDATION_TASKS, iteration, "val"))

        accepted = score > best
        previous_best = best
        if accepted:
            best = score
            print(f"  4. gate            {score:.0%} > {previous_best:.0%} previous -> KEPT")
        else:
            with open(SKILL_FILE, "w", encoding="utf-8") as handle:
                handle.write(previous)
            print(f"  4. gate            {score:.0%} <= {previous_best:.0%} previous -> ROLLED BACK")
        record_impact(iteration, score, previous_best, accepted, candidate)
        print("     (the wiki keeps what was learned either way)\n")

        if best >= 1.0:
            print("Validation is perfect; stopping early.\n")
            break

    print(f"{'=' * 62}")
    print(f"Baseline {baseline:.0%}  ->  final {best:.0%}")
    print("\nThe model never changed. Only the text around it did.\n")
    print(f"  {SKILL_FILE}\n     the skill it wrote for itself")
    print(f"  {os.path.join(PATTERNS)}\n     what it worked out along the way")
    print(f"  {IMPACT}\n     every proposal, kept or rolled back")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 5: an agent that writes its own skill.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--reset", action="store_true", help="delete the workspace first")
    args = parser.parse_args()

    if args.reset and os.path.isdir(WORKSPACE):
        shutil.rmtree(WORKSPACE)
        print("Workspace deleted; starting from nothing.\n")

    return evolve(args.model, args.iterations)


if __name__ == "__main__":
    sys.exit(main())

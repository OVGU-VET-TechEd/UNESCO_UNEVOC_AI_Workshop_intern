#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layer2_skill.py — Layer 2: the same task, with and without a skill file.

    python layer2_skill.py
    python layer2_skill.py --model qwen2.5-coder:14b

The conventions live in skills/objectives/SKILL.md next to this script (created
on first run; edit it and run again). The task text never changes; only whether
the skill block is put in front of it.
"""

from __future__ import annotations

import os

import layer_common as lc

TASK = "Write one learning objective for a vocational training module on: hydraulic system safety."
SKILL_PATH = os.path.join(lc.HERE, "skills", "objectives", "SKILL.md")
DEFAULT_SKILL = """---
name: objectives
description: House rules for writing learning objectives in vocational training modules.
---
# Writing learning objectives
- Begin with an approved action verb (identify, describe, explain, demonstrate, inspect, assess).
- Use at most 20 words.
- Write exactly one sentence.
- Reply with the sentence only, no preamble.
"""


def load_skill() -> str:
    if not os.path.exists(SKILL_PATH):
        os.makedirs(os.path.dirname(SKILL_PATH), exist_ok=True)
        with open(SKILL_PATH, "w", encoding="utf-8") as handle:
            handle.write(DEFAULT_SKILL)
    return lc.read(SKILL_PATH)


def build_prompt(task: str, skill: str | None) -> str:
    parts = []
    if skill:
        parts.append(f"Follow this guidance exactly:\n---\n{skill.strip()}\n---")
    parts.append(f"Task: {task}")
    return "\n\n".join(parts)


def main() -> int:
    args = lc.parse_args(__doc__.splitlines()[1])
    lc.require_model(args.model)
    skill = load_skill()

    sections = [f"Skill file: `{os.path.relpath(SKILL_PATH, lc.ROOT)}`\n\n{lc.fence(skill)}"]
    results = []
    for variant, label, skill_text in (("without skill", "Skill file: not loaded", None),
                                       ("with skill", "Skill file: loaded", skill)):
        prompt = build_prompt(TASK, skill_text)
        reply = lc.generate(args.model, prompt, num_predict=200)
        answer = reply.get("response", "").strip()
        ok, reason = lc.verify(answer)
        verdict = "Passes all three house rules." if ok else f"Fails: {reason}."
        results.append({"variant": variant, "prompt": prompt, "answer": answer, "passed": ok,
                        "reason": reason, "words": len(answer.split()), **lc.call_stats(reply)})
        blocks = 2 if skill_text else 1
        print(f"--- {label} ---")
        print(f"prompt = {'SKILL.md + ' if skill_text else ''}your task  "
              f"({blocks} block{'s' if blocks > 1 else ''}, {reply.get('prompt_eval_count', '?')} tokens)\n")
        print(f"{answer}\n\n{verdict}\n")
        sections.append(f"## {label}\n\n**Prompt sent** ({reply.get('prompt_eval_count', '?')} tokens):"
                        f"\n\n{lc.fence(prompt)}\n\n**Reply:**\n\n{lc.fence(answer)}\n\n"
                        f"**Check:** {verdict}")

    sections.append("Same model, same task. Only the skill block differed. A capable model may "
                    "pass even without the skill — run it several times, or with a smaller "
                    "model (e.g. `phi3`), to see the difference the file makes.")
    lc.write_report("layer2_skill.md", "Layer 2 — skill engineering", args.model,
                    "\n\n".join(sections))
    lc.write_data("layer2_skill", args.model,
                  {"skill_file": os.path.relpath(SKILL_PATH, lc.ROOT), "results": results})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layer1_prompt.py — Layer 1: one instruction, one call. Vague vs. specific.

    python layer1_prompt.py
    python layer1_prompt.py --model gemma3:12b

Sends the page's two prompts to the local model and reports the replies. The
three house rules are checked AFTERWARDS and only reported — at layer 1 nothing
in the system checks anything; that is the point.
"""

from __future__ import annotations

import layer_common as lc

# Exactly the two prompts from the page.
PROMPTS = {
    "vague": "Write a learning objective about hydraulic safety.",
    "specific": ("Write one learning objective for an apprentice mechanics module on hydraulic "
                 "system safety. Start with an action verb, use at most 20 words, and write "
                 "exactly one sentence. Reply with the sentence only."),
}


def main() -> int:
    args = lc.parse_args(__doc__.splitlines()[1])
    lc.require_model(args.model)

    sections = []
    results = []
    for kind, prompt in PROMPTS.items():
        print(f"--- {kind} prompt ---\n{prompt}\n")
        reply = lc.generate(args.model, prompt, num_predict=200)
        answer = reply.get("response", "").strip()
        ok, reason = lc.verify(answer)
        verdict = "Usable: passes all three house rules." if ok else f"Not usable: {reason}."
        results.append({"kind": kind, "prompt": prompt, "answer": answer, "passed": ok,
                        "reason": reason, "words": len(answer.split()), **lc.call_stats(reply)})
        print(f"POST {lc.OLLAMA_URL}/api/generate  model={args.model}")
        print(f"prompt: {reply.get('prompt_eval_count', '?')} tokens\n\n{answer}\n\n{verdict}\n")
        sections.append(f"## {kind.capitalize()} prompt\n\n{lc.fence(prompt)}\n\n"
                        f"**Reply** ({reply.get('prompt_eval_count', '?')} prompt tokens):\n\n"
                        f"{lc.fence(answer)}\n\n**Checked afterwards:** {verdict}")

    sections.append("Nothing in this layer checked the answers before you saw them. "
                    "The model has already forgotten both calls.")
    lc.write_report("layer1_prompt.md", "Layer 1 — prompt engineering", args.model,
                    "\n\n".join(sections))
    lc.write_data("layer1_prompt", args.model, {"results": results})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

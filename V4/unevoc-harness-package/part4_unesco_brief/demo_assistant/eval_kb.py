#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eval_kb.py — measure the assistant instead of admiring it.

USAGE
    python eval_kb.py --model llama3.1:8b
    python eval_kb.py --model qwen2.5:7b --kb kb_embed.json
    python eval_kb.py --model llama3.1:8b --questions eval_questions.json

WHY THIS FILE EXISTS
    "It gave a good answer when I tried it" is not evidence. This script runs a
    fixed set of questions and reports three numbers that actually matter:

        RETRIEVAL HIT   did the right document reach the prompt at all?
                        If it did not, no model can save the answer.
        REFUSAL         did the assistant decline the questions it should decline?
                        Measured separately, because a system that answers
                        everything scores well on the wrong metric.
        CITATION        did the answer carry markers that survive checking?

    Report all three. A single "accuracy" figure hides which of the three broke.

WHAT IT DOES NOT MEASURE
    Whether the prose is any good, whether the answer is *useful*, or whether a
    correct citation was used correctly. Those need a person. This harness tells
    you where to look; it does not tell you the system is fit for purpose.

    Add your own questions. Twelve is a demonstration; thirty to fifty real
    questions from real staff is a pilot.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import time

import ask as assistant

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the assistant against a fixed set.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--kb", default=os.path.join(HERE, "kb.json"))
    parser.add_argument("--questions", default=os.path.join(HERE, "eval_questions.json"))
    parser.add_argument("--output", default=os.path.join(HERE, "eval_report.md"))
    args = parser.parse_args()

    kb = assistant.load_kb(args.kb)
    with open(args.questions, "r", encoding="utf-8") as handle:
        questions = json.load(handle)["questions"]

    rows: list[dict] = []
    started = time.time()

    for index, item in enumerate(questions, start=1):
        print(f"[{index}/{len(questions)}] {item['question']}")
        result = assistant.answer_question(kb, item["question"], args.model)

        answered = result["status"] == "answered"
        refused = result["status"].startswith("refused")

        # Did the expected document reach the prompt?
        if item.get("expect_doc"):
            retrieval_hit = any(item["expect_doc"] in p["doc"] for p in result["passages"])
        else:
            retrieval_hit = None      # not applicable for refusal questions

        behaviour_ok = (answered if item["expect"] == "answered" else refused)

        rows.append({
            "question": item["question"],
            "expected": item["expect"],
            "status": result["status"],
            "behaviour_ok": behaviour_ok,
            "retrieval_hit": retrieval_hit,
            "attempts": result["attempts"],
            "top_doc": result["passages"][0]["doc"] if result["passages"] else "—",
            "top_score": result["passages"][0]["score"] if result["passages"] else 0.0,
            "answer": result["answer"],
        })
        print(f"      -> {result['status']}"
              + (f", retrieval hit: {retrieval_hit}" if retrieval_hit is not None else ""))

    elapsed = time.time() - started

    applicable = [r for r in rows if r["retrieval_hit"] is not None]
    retrieval_rate = (sum(1 for r in applicable if r["retrieval_hit"]) / len(applicable)
                      if applicable else 0.0)
    should_refuse = [r for r in rows if r["expected"] == "refused"]
    refusal_rate = (sum(1 for r in should_refuse if r["status"].startswith("refused"))
                    / len(should_refuse) if should_refuse else 0.0)
    should_answer = [r for r in rows if r["expected"] == "answered"]
    answer_rate = (sum(1 for r in should_answer if r["status"] == "answered")
                   / len(should_answer) if should_answer else 0.0)
    retries = sum(1 for r in rows if r["attempts"] > 1)

    lines = [
        "# Evaluation report", "",
        f"Run {_dt.datetime.now():%Y-%m-%d %H:%M} · model `{args.model}` · "
        f"knowledge base `{os.path.basename(args.kb)}` · "
        f"embeddings `{kb.get('embedding_model') or 'none'}` · "
        f"{len(kb['chunks'])} passages from {len(kb['documents'])} documents · "
        f"{elapsed:.0f} s", "",
        "## Headline numbers", "",
        "| Measure | Result | What it means |",
        "|---|---|---|",
        f"| Retrieval hit rate | **{retrieval_rate:.0%}** ({sum(1 for r in applicable if r['retrieval_hit'])}/{len(applicable)}) | "
        "the expected document reached the prompt. If this is low, fix chunking or retrieval, not the model. |",
        f"| Answered when it should | **{answer_rate:.0%}** ({sum(1 for r in should_answer if r['status'] == 'answered')}/{len(should_answer)}) | "
        "questions the corpus covers actually got an answer. |",
        f"| Refused when it should | **{refusal_rate:.0%}** ({sum(1 for r in should_refuse if r['status'].startswith('refused'))}/{len(should_refuse)}) | "
        "questions outside the corpus were declined rather than invented. |",
        f"| Answers needing a retry | {retries}/{len(rows)} | "
        "the citation check rejected a first attempt. |",
        "",
        "Report these three separately. A single blended figure hides which one broke.",
        "", "## Per question", "",
        "| # | Question | Expected | Result | Right doc retrieved | Top passage |",
        "|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(rows, start=1):
        hit = "—" if row["retrieval_hit"] is None else ("yes" if row["retrieval_hit"] else "**no**")
        mark = "" if row["behaviour_ok"] else " ⚠"
        lines.append(f"| {index} | {row['question']} | {row['expected']} | "
                     f"{row['status']}{mark} | {hit} | "
                     f"{row['top_doc']} ({row['top_score']}) |")

    lines += ["", "## Answers in full", ""]
    for index, row in enumerate(rows, start=1):
        lines += [f"**{index}. {row['question']}**", "",
                  f"> {row['answer']}", ""]

    lines += ["---", "",
              "**What this report does not tell you.** Whether the prose is good, "
              "whether a correct citation was used correctly, or whether the answer "
              "is useful for the job someone actually has. Those require a person to "
              "read the answers above. This harness tells you where to look.", ""]

    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print(f"\nRetrieval hit rate: {retrieval_rate:.0%}")
    print(f"Answered when expected: {answer_rate:.0%}")
    print(f"Refused when expected: {refusal_rate:.0%}")
    print(f"\nReport: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

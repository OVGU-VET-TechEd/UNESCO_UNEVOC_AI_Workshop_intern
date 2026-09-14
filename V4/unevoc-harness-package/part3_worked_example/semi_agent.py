#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
semi_agent.py — VARIANT A: a human-in-the-loop pipeline.

WHAT MAKES THIS A "SEMI-AGENT"
    The order of the steps is fixed, and a human wrote it. The program never
    decides what to do next. It never retries. If a step produces something
    strange, it produces that strange thing and moves on — and you see it,
    because every step leaves a file on disk before the next one starts.

    That is not a weakness. For most institutional work it is the correct design:
    it is auditable, it is predictable, and the human checkpoint before the report
    is a real decision point, not a formality.

THE FIXED SEQUENCE
    1  list the PDFs                     -> 01_manifest.json
    2  convert each PDF to Markdown      -> markdown/*.md
    3  summarise each Markdown file      -> summaries/*.txt      [model call]
    4  merge everything into a dataset   -> 02_dataset.json
    5  HUMAN CONFIRMS                    <- you type y
    6  write the report                  -> report.md, report.html, report.pdf

USAGE
    python make_sample_pdfs.py                 # once, to create input_pdfs/
    python semi_agent.py --model llama3.1:8b
    python semi_agent.py --model qwen2.5:7b --pause   # stop after every step
    python semi_agent.py --model qwen2.5:7b --yes     # skip the confirmation

COMPARE WITH
    agent.py — same task, same tools, but the program chooses the order itself
    and stops itself. Run both; read agent_log.md afterwards.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

import common

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(HERE, "input_pdfs")
OUTPUT_DIR = os.path.join(HERE, "output_semi")

SUMMARY_PROMPT = """You are summarising one document for a safety and training report.

Write 2 to 3 sentences of plain prose. State what the document is about and what
its figures show. Do not invent numbers that are not in the text. Do not use
bullet points, headings, or a preamble such as "This document".

Document:
---
{content}
---

Summary:"""


def step_header(number: int, title: str) -> None:
    print(f"\n{'=' * 68}\nSTEP {number} — {title}\n{'=' * 68}")


def pause_if_requested(paused: bool, artefact: str) -> None:
    print(f"  -> inspect: {artefact}")
    if paused:
        input("     press Enter to continue to the next step ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Variant A: fixed pipeline, human in the loop.")
    parser.add_argument("--model", required=True, help="Ollama model tag for the summary step")
    parser.add_argument("--input", default=INPUT_DIR, help="folder of PDFs to ingest")
    parser.add_argument("--output", default=OUTPUT_DIR, help="folder for all outputs")
    parser.add_argument("--pause", action="store_true", help="stop after every step")
    parser.add_argument("--yes", action="store_true", help="skip the human confirmation")
    args = parser.parse_args()

    common.require_model(args.model)

    out = args.output
    os.makedirs(os.path.join(out, "markdown"), exist_ok=True)
    os.makedirs(os.path.join(out, "summaries"), exist_ok=True)

    started = _dt.datetime.now()
    provenance: list[str] = [
        f"Pipeline: semi-agent (fixed sequence, human checkpoint), run {started:%Y-%m-%d %H:%M}",
    ]

    # -----------------------------------------------------------------------
    # STEP 1 — list the PDFs
    # -----------------------------------------------------------------------
    step_header(1, "Ingest: list the PDFs")
    pdfs = sorted(f for f in os.listdir(args.input) if f.lower().endswith(".pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {args.input}. Run make_sample_pdfs.py first.")
    manifest_path = os.path.join(out, "01_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump({"input_folder": args.input, "pdfs": pdfs}, handle, indent=2)
    for name in pdfs:
        print(f"  found {name}")
    pause_if_requested(args.pause, manifest_path)

    # -----------------------------------------------------------------------
    # STEP 2 — PDF to Markdown (required; sets the ceiling for everything after)
    # -----------------------------------------------------------------------
    step_header(2, "Convert each PDF to Markdown")
    markdown_paths: dict[str, str] = {}
    for name in pdfs:
        markdown_text = common.pdf_to_markdown(os.path.join(args.input, name))
        target = os.path.join(out, "markdown", name[:-4] + ".md")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(markdown_text)
        markdown_paths[name] = target
        print(f"  {name} -> {os.path.basename(target)}  ({len(markdown_text)} characters)")
    pause_if_requested(args.pause, os.path.join(out, "markdown"))

    # -----------------------------------------------------------------------
    # STEP 3 — summarise (the ONLY step that calls a model)
    # -----------------------------------------------------------------------
    step_header(3, f"Summarise each document with `{args.model}`")
    summaries: dict[str, str] = {}
    for name in pdfs:
        with open(markdown_paths[name], "r", encoding="utf-8") as handle:
            content = handle.read()
        # Keep the prompt small so this stays fast on a laptop CPU.
        prompt = SUMMARY_PROMPT.format(content=content[:4000])
        print(f"  asking the model about {name} ...")
        summary = common.call_ollama(args.model, prompt, num_predict=200)
        summaries[name] = summary
        target = os.path.join(out, "summaries", name[:-4] + ".txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(f"[model: {args.model}]\n{summary}\n")
        print(f"    {summary[:90]}{'...' if len(summary) > 90 else ''}")
    provenance.append(f"All {len(pdfs)} summaries generated by `{args.model}`")
    pause_if_requested(args.pause, os.path.join(out, "summaries"))

    # -----------------------------------------------------------------------
    # STEP 4 — merge into one dataset
    # -----------------------------------------------------------------------
    step_header(4, "Merge into one dataset")
    documents: list[dict] = []
    for name in pdfs:
        with open(markdown_paths[name], "r", encoding="utf-8") as handle:
            markdown_text = handle.read()
        rows = common.extract_tables_from_markdown(markdown_text)
        documents.append({
            "name": name[:-4].replace("_", " "),
            "source": name,
            "summary": summaries[name],
            "model": args.model,
            "rows": rows,
        })
        print(f"  {name}: {len(rows)} table rows extracted")
    dataset_path = os.path.join(out, "02_dataset.json")
    with open(dataset_path, "w", encoding="utf-8") as handle:
        json.dump(documents, handle, indent=2, ensure_ascii=False)
    pause_if_requested(args.pause, dataset_path)

    # -----------------------------------------------------------------------
    # STEP 5 — the human checkpoint. This is what makes it a SEMI-agent.
    # -----------------------------------------------------------------------
    step_header(5, "Human confirmation")
    print(f"  {len(documents)} documents, "
          f"{sum(len(d['rows']) for d in documents)} data rows, "
          f"{len(summaries)} summaries.")
    print(f"  Open {dataset_path} and check the summaries before continuing.")
    if args.yes:
        print("  --yes was passed; continuing without asking.")
    else:
        answer = input("  Generate the report from this data? [y/N] ").strip().lower()
        if answer != "y":
            print("\n  Stopped at the human checkpoint. Nothing was written.")
            print("  Fix the inputs, then run again.")
            return 2

    # -----------------------------------------------------------------------
    # STEP 6 — write the report
    # -----------------------------------------------------------------------
    step_header(6, "Write the report")
    paths = common.write_report_files(
        out_dir=out,
        title="Annual Safety and Training — Combined Report",
        subtitle=f"Semi-agent pipeline · {len(documents)} source documents · "
                 f"generated {started:%Y-%m-%d}",
        documents=documents,
        provenance=provenance,
    )
    for kind, path in paths.items():
        print(f"  {kind:9s} {path}")

    elapsed = (_dt.datetime.now() - started).total_seconds()
    print(f"\nFinished in {elapsed:.0f} s. Open {paths['html']} to see the table and chart.")
    print("Now run:  python agent.py --model <model>   and compare the two.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

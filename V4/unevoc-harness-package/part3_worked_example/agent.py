#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent.py — VARIANT B: the same task, run as a control loop.

WHAT MAKES THIS AN "AGENT"
    Nobody wrote the order of the steps. Each time round the loop, the model is
    shown the current state and the five tools it may use, and it proposes ONE
    next action. The harness then does four things the model is not trusted to do:

        1  CHECKS the proposal is legal (known tool, valid target, precondition met)
        2  EXECUTES the tool itself — the model never touches the filesystem
        3  VERIFIES the result (the file exists and is not empty) before recording it
        4  DECIDES whether to stop, using a written rule

    If the model proposes something illegal, the harness overrides it with the
    next required action and writes down that it did so. The loop therefore always
    terminates, and you can read exactly where the model helped and where it did not.

THE STOP CONDITION (this is the important part)
    Stop when report.md exists and contains a section for every input PDF.
    Plus a hard cap of MAX_STEPS as a second line of defence. An agent without a
    written stop condition is not an agent; it is a bill.

THE FIVE TOOLS
    list_pdfs            find the input documents
    convert_pdf_to_md    PDF -> Markdown (required ingestion step)
    summarize_md         Markdown -> a short summary        [the only model call]
    extract_table_data   Markdown -> rows of numbers
    write_report         everything -> report.md / .html / .pdf

USAGE
    python make_sample_pdfs.py                       # once
    python agent.py --model qwen2.5:7b
    python agent.py --model qwen2.5:7b --reset       # forget previous state
    python agent.py --model qwen2.5:7b --no-planner  # skip the model's proposals

READ AFTERWARDS
    output_agent/agent_log.md — a plain-language record of every decision and why.
    It is a teaching artefact in its own right; read it aloud in the session.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys

import common

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(HERE, "input_pdfs")
OUTPUT_DIR = os.path.join(HERE, "output_agent")

MAX_STEPS = 40              # hard cap: the loop can never run away
SUMMARY_CHAR_LIMIT = 4000   # how much of a document goes into the summary prompt

TOOL_NAMES = ["list_pdfs", "convert_pdf_to_md", "summarize_md",
              "extract_table_data", "write_report"]


# ===========================================================================
# HARNESS PART 1 — STATE
# ===========================================================================

def load_state(out_dir: str, model: str, input_dir: str) -> dict:
    """Read state from disk, or start a fresh one."""
    path = os.path.join(out_dir, "state.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            state["model"] = model          # the model may change between runs
            return state
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "model": model,
        "input_folder": input_dir,
        "pdfs": [],
        "converted": {},      # pdf name -> markdown path
        "summarised": {},     # pdf name -> {"summary": ..., "model": ...}
        "tables": {},         # pdf name -> list of row dicts
        "report_written": False,
        "steps_taken": 0,
    }


def save_state(out_dir: str, state: dict) -> None:
    """Write state after every single step, so an interrupted run resumes."""
    with open(os.path.join(out_dir, "state.json"), "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)


# ===========================================================================
# HARNESS PART 2 — THE LOG, in sentences a non-programmer can read
# ===========================================================================

class Log:
    def __init__(self, path: str, model: str) -> None:
        self.path = path
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(
                f"\n# Agent run — {_dt.datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
                f"Model used for planning and summarising: `{model}`.\n"
                f"Everything below was written by the program as it ran.\n\n"
            )

    def write(self, text: str) -> None:
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print(text.replace("**", ""))

    def step(self, number: int, title: str) -> None:
        self.write(f"\n## Step {number} — {title}\n")


# ===========================================================================
# HARNESS PART 3 — THE TOOLS
# ===========================================================================
# Each tool returns (ok, message, produced_file_or_None). Tools never decide what
# happens next; they only do one thing and report what happened.

def tool_list_pdfs(state: dict, target: str, out_dir: str) -> tuple[bool, str, str | None]:
    folder = state["input_folder"]
    if not os.path.isdir(folder):
        return False, f"the input folder {folder} does not exist", None
    pdfs = sorted(f for f in os.listdir(folder) if f.lower().endswith(".pdf"))
    state["pdfs"] = pdfs
    manifest = os.path.join(out_dir, "manifest.json")
    with open(manifest, "w", encoding="utf-8") as handle:
        json.dump({"input_folder": folder, "pdfs": pdfs}, handle, indent=2)
    return True, f"found {len(pdfs)} PDF file(s): {', '.join(pdfs)}", manifest


def tool_convert(state: dict, target: str, out_dir: str) -> tuple[bool, str, str | None]:
    source = os.path.join(state["input_folder"], target)
    markdown_text = common.pdf_to_markdown(source)
    destination = os.path.join(out_dir, "markdown", target[:-4] + ".md")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(markdown_text)
    state["converted"][target] = destination
    return True, (f"converted {target} to Markdown "
                  f"({len(markdown_text)} characters, figures noted but not OCR'd)"), destination


def tool_summarize(state: dict, target: str, out_dir: str) -> tuple[bool, str, str | None]:
    with open(state["converted"][target], "r", encoding="utf-8") as handle:
        content = handle.read()
    prompt = (
        "You are summarising one document for a safety and training report.\n\n"
        "Write 2 to 3 sentences of plain prose. State what the document is about and "
        "what its figures show. Do not invent numbers that are not in the text. No "
        "bullet points, no headings, no preamble.\n\nDocument:\n---\n"
        f"{content[:SUMMARY_CHAR_LIMIT]}\n---\n\nSummary:"
    )
    summary = common.call_ollama(state["model"], prompt, num_predict=200)   # MODEL CALL
    destination = os.path.join(out_dir, "summaries", target[:-4] + ".txt")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(f"[model: {state['model']}]\n{summary}\n")
    state["summarised"][target] = {"summary": summary, "model": state["model"]}
    return True, (f"summarised {target} using `{state['model']}` "
                  f"({len(summary.split())} words)"), destination


def tool_extract_tables(state: dict, target: str, out_dir: str) -> tuple[bool, str, str | None]:
    with open(state["converted"][target], "r", encoding="utf-8") as handle:
        rows = common.extract_tables_from_markdown(handle.read())
    state["tables"][target] = rows
    destination = os.path.join(out_dir, "tables", target[:-4] + ".json")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    if not rows:
        return True, f"no tables found in {target}; recorded an empty result", destination
    return True, f"extracted {len(rows)} table row(s) from {target}", destination


def tool_write_report(state: dict, target: str, out_dir: str) -> tuple[bool, str, str | None]:
    documents = [{
        "name": name[:-4].replace("_", " "),
        "source": name,
        "summary": state["summarised"][name]["summary"],
        "model": state["summarised"][name]["model"],
        "rows": state["tables"].get(name, []),
    } for name in state["pdfs"]]

    models_used = sorted({d["model"] for d in documents})
    provenance = [
        "Pipeline: agent (control loop, self-terminating)",
        f"Summaries generated by: {', '.join(f'`{m}`' for m in models_used)}",
        f"Planning proposals from: `{state['model']}`",
        f"Steps taken: {state['steps_taken']}",
    ]
    paths = common.write_report_files(
        out_dir=out_dir,
        title="Annual Safety and Training — Combined Report",
        subtitle=f"Agent pipeline · {len(documents)} source documents · "
                 f"generated {_dt.datetime.now():%Y-%m-%d}",
        documents=documents,
        provenance=provenance,
    )
    state["report_written"] = True
    return True, ("wrote " + ", ".join(os.path.basename(p) for p in paths.values())), \
        paths["markdown"]


TOOLS = {
    "list_pdfs": tool_list_pdfs,
    "convert_pdf_to_md": tool_convert,
    "summarize_md": tool_summarize,
    "extract_table_data": tool_extract_tables,
    "write_report": tool_write_report,
}


# ===========================================================================
# HARNESS PART 4 — PRECONDITIONS, VERIFICATION, STOP CONDITION
# ===========================================================================

def precondition_ok(tool: str, target: str, state: dict) -> tuple[bool, str]:
    """May this action be taken right now? Plain rules, no AI involved."""
    if tool == "list_pdfs":
        if state["pdfs"]:
            return False, "the PDFs have already been listed"
        return True, ""
    if tool == "write_report":
        missing = [p for p in state["pdfs"]
                   if p not in state["summarised"] or p not in state["tables"]]
        if not state["pdfs"]:
            return False, "no PDFs have been listed yet"
        if missing:
            return False, (f"{len(missing)} document(s) are not ready yet "
                           f"({', '.join(missing)})")
        return True, ""

    if target not in state["pdfs"]:
        return False, f"'{target}' is not one of the input PDFs"
    if tool == "convert_pdf_to_md":
        if target in state["converted"]:
            return False, f"{target} has already been converted"
        return True, ""
    if tool in ("summarize_md", "extract_table_data"):
        if target not in state["converted"]:
            return False, f"{target} has not been converted to Markdown yet"
        done = state["summarised"] if tool == "summarize_md" else state["tables"]
        if target in done:
            return False, f"{target} has already had `{tool}` applied"
        return True, ""
    return False, f"'{tool}' is not a known tool"


def verify_output(path: str | None) -> tuple[bool, str]:
    """The verification step: the file must exist and must not be empty.

    Deliberately crude, and deliberately independent of the model. A step is only
    marked done when a real file with real bytes is on disk.
    """
    if path is None:
        return False, "the tool did not name an output file"
    if not os.path.exists(path):
        return False, f"the expected file {os.path.basename(path)} was not created"
    size = os.path.getsize(path)
    if size == 0:
        return False, f"{os.path.basename(path)} was created but is empty"
    return True, f"{os.path.basename(path)} exists and holds {size} bytes"


def should_stop(state: dict, out_dir: str) -> tuple[bool, str]:
    """THE STOP CONDITION. Every input PDF must appear in the finished report."""
    report = os.path.join(out_dir, "report.md")
    if not state["report_written"] or not os.path.exists(report):
        return False, "the report has not been written yet"
    with open(report, "r", encoding="utf-8") as handle:
        text = handle.read()
    missing = [p for p in state["pdfs"]
               if not re.search(r"^###\s+" + re.escape(p[:-4].replace("_", " ")),
                                text, re.MULTILINE)]
    if missing:
        return False, f"{len(missing)} document(s) are missing from the report"
    return True, (f"the report exists and contains a section for all "
                  f"{len(state['pdfs'])} input documents")


def next_required_action(state: dict) -> tuple[str, str]:
    """The harness's own answer to 'what now?'.

    Used when the model's proposal is illegal, and as the whole planner when
    --no-planner is passed. This function is why the loop always terminates.
    """
    if not state["pdfs"]:
        return "list_pdfs", ""
    for name in state["pdfs"]:
        if name not in state["converted"]:
            return "convert_pdf_to_md", name
    for name in state["pdfs"]:
        if name not in state["summarised"]:
            return "summarize_md", name
    for name in state["pdfs"]:
        if name not in state["tables"]:
            return "extract_table_data", name
    return "write_report", ""


# ===========================================================================
# HARNESS PART 5 — ASKING THE MODEL WHAT TO DO NEXT
# ===========================================================================

def describe_state(state: dict) -> str:
    """A compact, honest picture of the world for the model to reason about."""
    if not state["pdfs"]:
        return "No PDFs have been listed yet."
    lines = []
    for name in state["pdfs"]:
        done = []
        if name in state["converted"]:
            done.append("converted")
        if name in state["summarised"]:
            done.append("summarised")
        if name in state["tables"]:
            done.append("tables extracted")
        lines.append(f"- {name}: {', '.join(done) if done else 'nothing done yet'}")
    lines.append(f"- report written: {'yes' if state['report_written'] else 'no'}")
    return "\n".join(lines)


def propose_action(state: dict) -> tuple[str, str, str] | None:
    """Ask the model for ONE next action. Returns (tool, target, why) or None.

    This is a model call. Its output is a suggestion, never a command: the
    harness validates it before anything happens.
    """
    prompt = (
        "You are choosing the next single action in a document-processing pipeline.\n\n"
        "Available tools:\n"
        "  list_pdfs            - list the input PDFs (no target)\n"
        "  convert_pdf_to_md    - convert one PDF to Markdown (target: the pdf filename)\n"
        "  summarize_md         - summarise one converted document (target: the pdf filename)\n"
        "  extract_table_data   - pull tables from one converted document (target: the pdf filename)\n"
        "  write_report         - write the final report (no target); only when every\n"
        "                         document has been summarised AND had tables extracted\n\n"
        "Current state:\n"
        f"{describe_state(state)}\n\n"
        "Reply with one line of JSON and nothing else, in this exact form:\n"
        '{"tool": "<tool name>", "target": "<pdf filename or empty string>", '
        '"why": "<one short sentence>"}\n'
    )
    try:
        reply = common.call_ollama(state["model"], prompt, num_predict=120, temperature=0.1)
    except Exception:  # noqa: BLE001 — a failed proposal is not fatal; the harness copes
        return None

    match = re.search(r"\{.*?\}", reply, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    tool = str(parsed.get("tool", "")).strip()
    target = str(parsed.get("target", "") or "").strip()
    why = str(parsed.get("why", "") or "no reason given").strip()
    return tool, target, why


# ===========================================================================
# HARNESS PART 6 — THE LOOP ITSELF
# ===========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Variant B: control loop, agent decides.")
    parser.add_argument("--model", required=True, help="Ollama model tag")
    parser.add_argument("--input", default=INPUT_DIR)
    parser.add_argument("--output", default=OUTPUT_DIR)
    parser.add_argument("--reset", action="store_true", help="delete state and start over")
    parser.add_argument("--no-planner", action="store_true",
                        help="skip the model's proposals; the harness decides every step")
    args = parser.parse_args()

    common.require_model(args.model)
    os.makedirs(args.output, exist_ok=True)

    if args.reset:
        for name in ("state.json", "agent_log.md"):
            path = os.path.join(args.output, name)
            if os.path.exists(path):
                os.remove(path)

    state = load_state(args.output, args.model, args.input)
    log = Log(os.path.join(args.output, "agent_log.md"), args.model)

    log.write(
        "The rule I follow: I may take one action per step. Before acting I check "
        "that the action is allowed. After acting I check that a real, non-empty "
        f"file was produced. I stop when the report contains a section for every "
        f"input PDF, or after {MAX_STEPS} steps, whichever comes first."
    )

    step = 0
    while step < MAX_STEPS:
        stop, reason = should_stop(state, args.output)
        if stop:
            log.write(f"\n**Stopping.** {reason.capitalize()}. "
                      f"The stop condition is met, so there is nothing left to do.")
            break

        step += 1
        state["steps_taken"] = state.get("steps_taken", 0) + 1
        log.step(step, "choosing an action")

        # --- 1. propose ----------------------------------------------------
        required_tool, required_target = next_required_action(state)
        if args.no_planner:
            tool, target = required_tool, required_target
            log.write(f"The planner is switched off, so I take the next required "
                      f"action myself: `{tool}`"
                      + (f" on `{target}`." if target else "."))
        else:
            proposal = propose_action(state)
            if proposal is None:
                tool, target = required_tool, required_target
                log.write("I asked the model what to do next and could not read a "
                          "usable answer out of its reply. **I overrode it** and took "
                          f"the next required action instead: `{tool}`"
                          + (f" on `{target}`." if target else "."))
            else:
                tool, target, why = proposal
                log.write(f"The model proposed `{tool}`"
                          + (f" on `{target}`" if target else "")
                          + f", because: \"{why}\"")

                # --- 2. check the proposal is legal ------------------------
                if tool not in TOOLS:
                    log.write(f"  `{tool}` is not one of my five tools. "
                              f"**I overrode the proposal** and will do "
                              f"`{required_tool}`"
                              + (f" on `{required_target}`" if required_target else "")
                              + " instead.")
                    tool, target = required_tool, required_target
                else:
                    allowed, why_not = precondition_ok(tool, target, state)
                    if not allowed:
                        log.write(f"  I checked whether that is allowed right now: it is "
                                  f"not, because {why_not}. **I overrode the proposal** "
                                  f"and will do `{required_tool}`"
                                  + (f" on `{required_target}`" if required_target else "")
                                  + " instead.")
                        tool, target = required_tool, required_target
                    else:
                        log.write("  I checked the preconditions and they hold, "
                                  "so I will do exactly that.")

        # --- 3. execute ----------------------------------------------------
        try:
            ok, message, produced = TOOLS[tool](state, target, args.output)
        except Exception as error:  # noqa: BLE001 — record it and let verification fail
            ok, message, produced = False, f"the tool raised {type(error).__name__}: {error}", None

        log.write(f"  I ran `{tool}`. Result: {message}.")

        # --- 4. verify -----------------------------------------------------
        verified, verification_message = (False, message) if not ok else verify_output(produced)
        if verified:
            log.write(f"  I verified the result: {verification_message}. "
                      f"Marking this step done.")
            save_state(args.output, state)
        else:
            log.write(f"  **Verification failed:** {verification_message}. "
                      f"I am NOT marking this step done; I will try the next required "
                      f"action on the following step.")
            # Undo the optimistic bookkeeping so the step is genuinely not done.
            for bucket in ("converted", "summarised", "tables"):
                state[bucket].pop(target, None)
            if tool == "write_report":
                state["report_written"] = False
            save_state(args.output, state)

    else:
        log.write(f"\n**Stopping.** I reached the hard limit of {MAX_STEPS} steps "
                  f"without meeting the stop condition. This limit exists so the loop "
                  f"can never run away; the work is incomplete and needs a human.")

    stop, reason = should_stop(state, args.output)
    log.write(f"\n---\n\n**Final state:** {reason}.\n")

    print(f"\nLog:    {os.path.join(args.output, 'agent_log.md')}")
    print(f"State:  {os.path.join(args.output, 'state.json')}")
    if os.path.exists(os.path.join(args.output, "report.html")):
        print(f"Report: {os.path.join(args.output, 'report.html')}")
    return 0 if stop else 1


if __name__ == "__main__":
    sys.exit(main())

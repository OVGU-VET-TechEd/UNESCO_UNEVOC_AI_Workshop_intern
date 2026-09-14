#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
min_harness.py — the smallest honest example of a harness.

WHAT THIS PROGRAM DOES
    It asks a local model (running in Ollama, on your own machine) to write one
    learning objective for each of three TVET topics. It then CHECKS each answer
    against three rules that a human wrote in advance. If an answer fails a rule,
    it asks again — up to three times — telling the model exactly what was wrong.
    Everything it does is written to a log file and a state file.

WHY IT LOOKS LIKE THIS
    Only about fifteen lines of this file send text to a model (see `call_ollama`).
    Everything else is the harness:

        STATE          harness_state.json  — what has already been accepted
        VERIFICATION   verify()            — the rules the answer must satisfy
        STOP CONDITION MAX_ATTEMPTS        — retries are bounded, never infinite
        LOG            harness_log.md      — a plain-language record of every attempt

    That four-part split is the entire lesson. Read the four functions below in
    that order and you have read a harness.

HOW TO RUN
    python min_harness.py --list-models              # what is installed here?
    python min_harness.py --model llama3.1:8b        # run with one model
    python min_harness.py --model qwen2.5:7b         # run with another
    python min_harness.py --model qwen2.5:7b --reset # forget previous results

    Runs in well under two minutes on a laptop CPU with a 7-8B model.

REQUIREMENTS
    Python 3.9+ and nothing else. Only the standard library is used, on purpose:
    a harness you cannot install is not a harness.
    Ollama must be running and reachable at http://127.0.0.1:11434 .
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# 1. CONFIGURATION — the single place a facilitator needs to edit
# ---------------------------------------------------------------------------

# The Ollama server. Local only. Nothing in this file ever calls the internet.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# The default model. Override on the command line with --model.
# This is the "single config variable" that switches models.
DEFAULT_MODEL = os.environ.get("HARNESS_MODEL", "llama3.1:8b")

# The stop condition for the retry loop. Never leave this unbounded.
MAX_ATTEMPTS = 3

# How long to wait for one model reply, in seconds. First call is slowest
# because the model is being loaded into memory.
TIMEOUT_SECONDS = 180

# Files the harness owns. They live next to this script.
HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "harness_state.json")
LOG_FILE = os.path.join(HERE, "harness_log.md")

# The work to be done. Three items keeps the demo under two minutes.
TOPICS = [
    "hydraulic system safety for apprentice mechanics",
    "reading an electrical circuit diagram",
    "workplace risk assessment in a metal workshop",
]

# The ground rules an answer must satisfy. These are the "definition of done".
# A human wrote them. The model never sees them as something it can negotiate.
ALLOWED_VERBS = [
    "identify", "describe", "explain", "demonstrate", "apply",
    "analyse", "analyze", "evaluate", "design", "calculate",
    "inspect", "select", "measure", "operate", "assess",
]
MAX_WORDS = 20


# ---------------------------------------------------------------------------
# 2. THE MODEL CALL — this, and only this, is "the AI part"
# ---------------------------------------------------------------------------

def call_ollama(model: str, prompt: str) -> str:
    """Send one prompt to the local model and return its reply as plain text.

    Everything else in this file is harness. This is the model call.
    """
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,              # we want one complete answer, not a stream
        "options": {
            "temperature": 0.2,       # low: we want obedience, not creativity
            "num_predict": 80,        # short answers keep the demo fast
        },
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body.get("response", "").strip()


def build_prompt(topic: str, previous_failure: str | None) -> str:
    """Write the instruction text. On a retry, the failure reason is included.

    Note what happens on a retry: we do NOT just ask again and hope. We tell the
    model precisely which rule it broke. That is the difference between a retry
    loop and a slot machine.
    """
    rules = (
        "Rules:\n"
        f"1. Start with exactly one of these verbs: {', '.join(ALLOWED_VERBS[:8])}.\n"
        f"2. Use at most {MAX_WORDS} words in total.\n"
        "3. Write exactly one sentence. No bullet points, no preamble, no quotation marks.\n"
    )
    task = (
        "Write one learning objective for a vocational training module on:\n"
        f"  {topic}\n\n{rules}\n"
        "Reply with the sentence only."
    )
    if previous_failure:
        task += (
            "\n\nYour previous answer was rejected for this reason:\n"
            f"  {previous_failure}\n"
            "Correct it and reply with the sentence only."
        )
    return task


# ---------------------------------------------------------------------------
# 3. VERIFICATION — the harness checking the model's homework
# ---------------------------------------------------------------------------

def verify(answer: str) -> tuple[bool, str]:
    """Check one answer against the ground rules.

    Returns (True, "ok") if the answer is acceptable, otherwise
    (False, "<plain-language reason>"). The reason is fed back into the retry
    prompt and written to the log, so a reader can see WHY something failed.

    This function contains no AI. It is ordinary, boring, readable code — and
    that is exactly why it can be trusted to judge the model's output.
    """
    text = answer.strip().strip('"').strip("'")

    if not text:
        return False, "the answer was empty"

    # Rule 3, part one: strip a leading bullet or numbering if the model added one.
    text = re.sub(r"^[-*\d.)\s]+", "", text)

    # Rule 1: must open with one of the allowed action verbs.
    first_word = re.split(r"[\s,.:;]+", text, maxsplit=1)[0].lower()
    if first_word not in ALLOWED_VERBS:
        return False, (
            f"it started with '{first_word}', which is not one of the allowed "
            f"action verbs ({', '.join(ALLOWED_VERBS[:8])})"
        )

    # Rule 2: length limit.
    word_count = len(text.split())
    if word_count > MAX_WORDS:
        return False, f"it was {word_count} words long; the limit is {MAX_WORDS}"

    # Rule 3, part two: exactly one sentence.
    sentence_endings = len(re.findall(r"[.!?](\s|$)", text))
    if sentence_endings > 1:
        return False, f"it contained {sentence_endings} sentences; exactly one is required"
    if "\n" in text.strip():
        return False, "it contained more than one line; exactly one sentence is required"

    return True, "ok"


# ---------------------------------------------------------------------------
# 4. STATE — memory that survives the program exiting
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Read what previous runs accomplished. Missing or broken file = start fresh."""
    if not os.path.exists(STATE_FILE):
        return {"accepted": {}, "runs": 0}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            state = json.load(handle)
        state.setdefault("accepted", {})
        state.setdefault("runs", 0)
        return state
    except (json.JSONDecodeError, OSError):
        return {"accepted": {}, "runs": 0}


def save_state(state: dict) -> None:
    """Write state to disk after every accepted answer, not only at the end.

    Written immediately so that killing the program mid-run loses at most one
    item. Try it: interrupt the run with Ctrl-C and start it again.
    """
    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 5. LOG — observability, in sentences a non-programmer can read
# ---------------------------------------------------------------------------

def log(line: str) -> None:
    """Append one plain-language line to the log file and to the screen."""
    stamp = _dt.datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(f"- `{stamp}` {line}\n")
    print(f"  {line}")


# ---------------------------------------------------------------------------
# 6. MODEL DISCOVERY — find out what is actually installed, do not assume
# ---------------------------------------------------------------------------

def installed_models() -> list[str]:
    """List models available on this machine.

    Asks the Ollama REST API first (works over an SSH tunnel to a remote server),
    and falls back to running `ollama list` locally if the API is unreachable.
    """
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        names = [m["name"] for m in data.get("models", [])]
        if names:
            return sorted(names)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        pass

    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=20, check=False
        )
        lines = result.stdout.strip().splitlines()[1:]  # skip the header row
        return sorted(line.split()[0] for line in lines if line.strip())
    except (OSError, subprocess.SubprocessError):
        return []


# ---------------------------------------------------------------------------
# 7. THE CONTROL FLOW — read this to understand the program
# ---------------------------------------------------------------------------

def process_topic(topic: str, model: str, state: dict) -> bool:
    """Get one acceptable learning objective for one topic. Returns success.

    The control flow, in words:
        Has this topic already been accepted in an earlier run?  -> skip it
        Otherwise, up to MAX_ATTEMPTS times:
            ask the model
            verify the answer
            if it passes -> record it, save state, stop asking
            if it fails  -> log the reason, put the reason in the next prompt
        If all attempts fail -> give up on this topic and say so clearly.
    """
    if topic in state["accepted"]:
        log(f"SKIP  '{topic}' — already accepted in an earlier run, nothing to do.")
        return True

    failure_reason: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        log(f"ASK   attempt {attempt} of {MAX_ATTEMPTS} for '{topic}' using model `{model}`.")
        try:
            answer = call_ollama(model, build_prompt(topic, failure_reason))
        except urllib.error.URLError as error:
            log(f"ERROR could not reach Ollama at {OLLAMA_URL} ({error}). Stopping.")
            raise SystemExit(
                f"\nOllama is not reachable at {OLLAMA_URL}.\n"
                "Start it with `ollama serve`, then run this script again.\n"
            )
        except Exception as error:  # noqa: BLE001 — demo code, report and move on
            failure_reason = f"the model call failed ({type(error).__name__})"
            log(f"ERROR {failure_reason}.")
            continue

        log(f"GOT   \"{answer[:100]}\"")

        passed, reason = verify(answer)
        if passed:
            log("CHECK passed all three rules. Accepting this answer.")
            state["accepted"][topic] = {
                "objective": answer.strip().strip('"'),
                "model": model,          # which model produced this, for the record
                "attempts_used": attempt,
                "accepted_at": _dt.datetime.now().isoformat(timespec="seconds"),
            }
            save_state(state)            # persist immediately, not at the end
            return True

        failure_reason = reason
        log(f"CHECK failed: {reason}. Re-asking with that reason included.")

    log(f"STOP  gave up on '{topic}' after {MAX_ATTEMPTS} attempts. "
        f"The retry limit is the stop condition — it is never unbounded.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="A minimal harness: state, verification, bounded retry, log."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model tag to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--list-models", action="store_true",
                        help="Show which models are installed here, then exit")
    parser.add_argument("--reset", action="store_true",
                        help="Delete the state file and start from scratch")
    args = parser.parse_args()

    available = installed_models()

    if args.list_models:
        if available:
            print("Models installed on this machine:")
            for name in available:
                print(f"  {name}")
        else:
            print(f"No models found. Is Ollama running at {OLLAMA_URL}?")
        return 0

    if args.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("State file deleted; starting from scratch.")

    # Fail early and helpfully rather than deep inside the loop.
    if available and args.model not in available:
        print(f"Model '{args.model}' is not installed on this machine.")
        print("Installed models: " + ", ".join(available))
        print(f"Pull it first:  ollama pull {args.model}")
        return 1
    if not available:
        print(f"Warning: could not list models from {OLLAMA_URL}. Trying anyway.\n")

    state = load_state()
    state["runs"] += 1
    save_state(state)

    header = (
        f"\n## Run {state['runs']} — "
        f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — model `{args.model}`\n\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(header)

    print(f"Harness run {state['runs']}, model '{args.model}', "
          f"{len(TOPICS)} topics, max {MAX_ATTEMPTS} attempts each.\n")

    succeeded = sum(process_topic(topic, args.model, state) for topic in TOPICS)

    print(f"\nDone. {succeeded} of {len(TOPICS)} topics have an accepted objective.")
    print(f"State: {STATE_FILE}")
    print(f"Log:   {LOG_FILE}")
    print("\nAccepted objectives so far:")
    for topic, record in state["accepted"].items():
        print(f"  [{record['model']}] {topic}\n      {record['objective']}")

    # Exit code 0 only when every topic succeeded, so this script can itself be
    # used as a verification command inside a larger harness.
    return 0 if succeeded == len(TOPICS) else 1


if __name__ == "__main__":
    sys.exit(main())

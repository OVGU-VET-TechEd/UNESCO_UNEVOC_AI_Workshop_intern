# -*- coding: utf-8 -*-
"""
layer_common.py — shared helpers for the layerN_*.py scripts.

The layer scripts produce, with YOUR local model, the outputs that
LEARN_the_five_layers.html only replays. Every report they write names the
model and the time, so real output is never confused with the page's canned text.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("HARNESS_MODEL", "llama3.1:8b")
TIMEOUT_SECONDS = 300

HERE = os.path.dirname(os.path.abspath(__file__))
PART5 = os.path.dirname(HERE)
ROOT = os.path.dirname(PART5)
OUTPUT = os.path.join(HERE, "output")


def _load_min_harness():
    """Reuse File D's rules, so every layer judges answers by the same code."""
    path = os.path.join(ROOT, "part2_teaching", "file_d_min_harness", "min_harness.py")
    spec = importlib.util.spec_from_file_location("min_harness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_harness = _load_min_harness()
verify = _harness.verify              # (answer) -> (ok, reason). Plain code, no model.
ALLOWED_VERBS = _harness.ALLOWED_VERBS
MAX_WORDS = _harness.MAX_WORDS


def parse_args(description: str, extra=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model tag (default {DEFAULT_MODEL})")
    if extra:
        extra(parser)
    return parser.parse_args()


def installed_models() -> list[str]:
    with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as response:
        return [m["name"] for m in json.loads(response.read().decode("utf-8")).get("models", [])]


def require_model(model: str) -> None:
    """Stop with a readable message if Ollama is down or the model is missing."""
    try:
        names = installed_models()
    except (urllib.error.URLError, OSError) as error:
        sys.exit(f"Ollama is not reachable at {OLLAMA_URL} ({error}).\n"
                 f"Start it with:  ollama serve")
    if model.startswith("mock:"):
        print("WARNING: mock model — the output below is CANNED, not model output.\n")
    if model not in names and f"{model}:latest" not in names:
        sys.exit(f"Model '{model}' is not installed. Installed: {', '.join(names) or 'none'}\n"
                 f"Pull it with:  ollama pull {model}")


def generate(model: str, prompt: str, **options) -> dict:
    """One call to the local model. Returns Ollama's full JSON reply."""
    raw = options.pop("raw", False)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "raw": raw,
                          "options": {"temperature": 0.2, **options}}).encode("utf-8")
    request = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=payload,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def ask(model: str, prompt: str) -> str:
    return generate(model, prompt, num_predict=120).get("response", "").strip()


def python_with_deps() -> str:
    """The package venv if run_package.py created one, else this interpreter."""
    venv = os.path.join(ROOT, ".venv", "Scripts" if os.name == "nt" else "bin",
                        "python.exe" if os.name == "nt" else "python")
    return venv if os.path.exists(venv) else sys.executable


def run_script(args: list[str], cwd: str) -> int:
    print(f"$ python {' '.join(args)}\n", flush=True)
    return subprocess.run([python_with_deps(), *args], cwd=cwd).returncode


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write_report(name: str, title: str, model: str, body: str) -> str:
    """Save a Markdown report with provenance, and return its path."""
    os.makedirs(OUTPUT, exist_ok=True)
    path = os.path.join(OUTPUT, name)
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    note = ("CANNED output from the mock server — not model output."
            if model.startswith("mock:") else
            f"Generated on this computer by the local model `{model}` via {OLLAMA_URL}.")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"# {title}\n\n> {note}  \n> Run: {stamp}\n\n{body.rstrip()}\n")
    print(f"\nReport: {os.path.relpath(path, ROOT)}")
    return path


def fence(text: str) -> str:
    return f"```text\n{text.rstrip()}\n```"


def call_stats(reply: dict) -> dict:
    """Token counts and wall time Ollama reports for one call."""
    return {"prompt_tokens": reply.get("prompt_eval_count"),
            "answer_tokens": reply.get("eval_count"),
            "seconds": round(reply.get("total_duration", 0) / 1e9, 2)}


def write_data(name: str, model: str, data: dict) -> str:
    """Save the lab's measured outcome as JSON, for run_all_layers.py to collect."""
    os.makedirs(OUTPUT, exist_ok=True)
    path = os.path.join(OUTPUT, f"{name}.json")
    record = {"lab": name, "model": model, "ollama_url": OLLAMA_URL,
              "run_at": _dt.datetime.now().isoformat(timespec="seconds"), "data": data}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
    return path


def ollama_version() -> str | None:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/version", timeout=10) as response:
            return json.loads(response.read().decode("utf-8")).get("version")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def model_details(model: str) -> dict:
    """Family, size and quantisation of an installed model, as Ollama reports them."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
    except (urllib.error.URLError, OSError, ValueError):
        return {}
    for entry in models:
        if entry.get("name") in (model, f"{model}:latest"):
            return {"digest": entry.get("digest", "")[:12], **entry.get("details", {})}
    return {}

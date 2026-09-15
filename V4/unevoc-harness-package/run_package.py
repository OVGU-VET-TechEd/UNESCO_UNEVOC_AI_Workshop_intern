#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_package.py — run the whole package, one step after another, from one file.

    python3 run_package.py                       # mock server, no model needed
    python3 run_package.py --model llama3.1:8b   # a real local Ollama model
    python3 run_package.py --no-venv             # use the current interpreter

It does what `make init` followed by `make demo` does, without needing `make`
or a POSIX shell, so it also works on Windows:

    1  environment   create .venv and install the Part 3 dependencies
    2  corpus        regenerate corpus_raw/ and run the anonymiser
    3  kb            rebuild kb.json from corpus/
    4  verify        tools/verify_package.py — the definition of done
    5  part 2        minimal harness
    6  part 3        sample PDFs, semi-agent, agent
    7  part 4        assistant evaluation
    8  part 5        self-improving agent

For a mock:* model (the default) it starts tools/mock_ollama.py on its own port
and stops it at the end. Output produced that way is CANNED, not model output.

Every step runs even if an earlier one fails; the summary at the end lists what
failed, and the exit code is non-zero if anything did.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(ROOT, "part4_unesco_brief", "demo_assistant")
PART3 = os.path.join(ROOT, "part3_worked_example")
VENV = os.path.join(ROOT, ".venv")


def banner(title: str) -> None:
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}", flush=True)


def venv_python() -> str:
    if os.name == "nt":
        return os.path.join(VENV, "Scripts", "python.exe")
    return os.path.join(VENV, "bin", "python")


def run(command: list[str], cwd: str = ROOT, env: dict | None = None) -> bool:
    print(f"$ {' '.join(os.path.basename(c) if i == 0 else c for i, c in enumerate(command))}",
          flush=True)
    return subprocess.run(command, cwd=cwd, env=env).returncode == 0


def setup_environment(use_venv: bool) -> tuple[str, bool]:
    """Return the interpreter to use for every later step, and whether setup worked."""
    if not use_venv:
        return sys.executable, run([sys.executable, "-m", "pip", "install", "-q", "-r",
                                    os.path.join(PART3, "requirements.txt")])
    if not os.path.exists(venv_python()):
        if not run([sys.executable, "-m", "venv", VENV]):
            return sys.executable, False
    python = venv_python()
    ok = run([python, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    ok = run([python, "-m", "pip", "install", "-q", "-r",
              os.path.join(PART3, "requirements.txt")]) and ok
    return python, ok


def start_mock(python: str, port: int) -> subprocess.Popen:
    """Start the mock Ollama server and wait until it answers, or raise."""
    log = open(os.path.join(ROOT, "mock_ollama.log"), "w", encoding="utf-8")
    env = dict(os.environ, MOCK_OLLAMA_PORT=str(port))
    process = subprocess.Popen([python, os.path.join(ROOT, "tools", "mock_ollama.py")],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/api/tags"
    for _ in range(20):
        if process.poll() is not None:
            break
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if b"mock:" in response.read():
                    print(f"mock server up on http://127.0.0.1:{port} (canned responses)")
                    return process
        except OSError:
            pass
        time.sleep(0.5)
    process.kill()
    raise RuntimeError(f"the mock server is not answering on port {port} "
                       f"(see mock_ollama.log; if the port is taken, use --mock-port 11500)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the whole package end to end.")
    parser.add_argument("--model", default="mock:demo",
                        help="Ollama model tag; mock:* starts the mock server (default mock:demo)")
    parser.add_argument("--mock-port", type=int, default=11435,
                        help="port for the mock server (default 11435)")
    parser.add_argument("--no-venv", action="store_true",
                        help="install into and run with the current interpreter")
    args = parser.parse_args()

    results: list[tuple[str, bool]] = []

    banner("1  Environment: virtual environment and dependencies")
    python, ok = setup_environment(use_venv=not args.no_venv)
    results.append(("environment", ok))

    banner("2  Corpus: generate raw documents and anonymise")
    ok = run([python, "make_corpus.py"], cwd=DEMO) and run([python, "anonymise.py"], cwd=DEMO)
    results.append(("corpus", ok))
    print(f"\n>>> READ {os.path.relpath(os.path.join(DEMO, 'anonymisation_report.md'), ROOT)} "
          f"before using this corpus for anything real.")

    banner("3  Knowledge base: build kb.json")
    results.append(("kb", run([python, "kb_build.py"], cwd=DEMO)))

    banner("4  Verify: tools/verify_package.py")
    results.append(("verify", run([python, os.path.join(ROOT, "tools", "verify_package.py")])))

    env = dict(os.environ)
    mock = None
    if args.model.startswith("mock:"):
        try:
            mock = start_mock(python, args.mock_port)
        except RuntimeError as error:
            print(f"ERROR: {error}")
            results.append(("mock server", False))
            return summary(results, mocked=True)
        env["OLLAMA_URL"] = f"http://127.0.0.1:{args.mock_port}"

    try:
        banner("5  Part 2: minimal harness")
        results.append(("part 2 min_harness", run(
            [python, os.path.join(ROOT, "part2_teaching", "file_d_min_harness", "min_harness.py"),
             "--model", args.model, "--reset"], env=env)))

        banner("6  Part 3: sample PDFs, semi-agent, agent")
        results.append(("part 3 sample PDFs", run([python, "make_sample_pdfs.py"],
                                                  cwd=PART3, env=env)))
        results.append(("part 3 semi_agent", run(
            [python, "semi_agent.py", "--model", args.model, "--yes"], cwd=PART3, env=env)))
        results.append(("part 3 agent", run(
            [python, "agent.py", "--model", args.model, "--reset"], cwd=PART3, env=env)))

        banner("7  Part 4: assistant evaluation")
        results.append(("part 4 eval_kb", run(
            [python, "eval_kb.py", "--model", args.model], cwd=DEMO, env=env)))

        banner("8  Part 5: self-improving agent")
        results.append(("part 5 wiki_agent", run(
            [python, "wiki_agent.py", "--model", args.model, "--reset", "--iterations", "5"],
            cwd=os.path.join(ROOT, "part5_self_improving"), env=env)))
    finally:
        if mock is not None:
            mock.terminate()
            mock.wait(timeout=5)

    return summary(results, mocked=mock is not None)


def summary(results: list[tuple[str, bool]], mocked: bool) -> int:
    banner("Summary")
    for name, ok in results:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    if mocked:
        print("\nOutput was CANNED (mock server) - not model output.")
    failed = [name for name, ok in results if not ok]
    if failed:
        print(f"\n{len(failed)} step(s) failed: {', '.join(failed)}")
        return 1
    print("\nAll steps completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

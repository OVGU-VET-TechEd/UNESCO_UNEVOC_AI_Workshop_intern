#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_package.py — the definition of done for this package.

    make verify        # or:  python tools/verify_package.py

Exits 0 if every check passes, 1 otherwise. This script is the single arbiter of
"is the package in a good state". Agents are instructed never to mark work done
without pasting its output as evidence, and `@qa` runs nothing else.

It is deliberately ordinary code. Nothing here calls a language model, because a
check a model performs on its own work is not a check.

CHECKS
    1  syntax        every .py file compiles
    2  json          every .json file parses
    3  structure     the files the runbooks and index reference actually exist
    4  offline       no code reaches a non-localhost network endpoint
    5  liascript     decks use working quiz syntax and carry speaker notes
    6  anonymisation the indexed corpus contains no unredacted direct identifiers
    7  knowledgebase kb.json parses, is non-empty, and matches its corpus
    8  links         relative Markdown links resolve
    9  agents        Copilot and Continue configuration is present, well-formed and local to files that exist

Add checks here as the package grows. A check you cannot run is not a standard.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".continue-cache"}

# Files whose absence breaks a runbook, the index, or a session.
REQUIRED = [
    "00_INDEX.md",
    "AGENTS.md",
    "Makefile",
    "part1_timeline/PART1_four_levels_timeline.md",
    "part2_teaching/FILE_A_harness_engineering_liascript.md",
    "part2_teaching/FILE_B_cheatsheet.md",
    "part2_teaching/FILE_B_cheatsheet.html",
    "part2_teaching/RUNBOOK_macOS.md",
    "part2_teaching/RUNBOOK_Windows.md",
    "part2_teaching/file_d_min_harness/min_harness.py",
    "part3_worked_example/common.py",
    "part3_worked_example/semi_agent.py",
    "part3_worked_example/agent.py",
    "part3_worked_example/make_sample_pdfs.py",
    "part4_unesco_brief/00_PART4_INDEX.md",
    "part4_unesco_brief/A_definitions_assistants_agents_knowledge_bases.md",
    "part4_unesco_brief/B_unevoc_use_cases.md",
    "part4_unesco_brief/C_pilot_selection_worksheet.md",
    "part4_unesco_brief/D_liascript_deck_assistants.md",
    "part4_unesco_brief/demo_assistant/ask.py",
    "part4_unesco_brief/demo_assistant/kb_build.py",
    "part4_unesco_brief/demo_assistant/anonymise.py",
    "part4_unesco_brief/demo_assistant/eval_kb.py",
    "part4_unesco_brief/demo_assistant/eval_questions.json",
    "part5_self_improving/wiki_agent.py",
    "part5_self_improving/LEARN_the_five_layers.html",
    "part5_self_improving/README.md",
    "tools/mock_ollama.py",
    "tools/verify_package.py",
    "feature_list.json",
    "PROGRESS.md",
    "bmad/README.md",
    "bmad/agents/curator.md",
    "bmad/agents/librarian.md",
    "bmad/agents/author.md",
    "bmad/agents/qa.md",
    "bmad/agents/packager.md",
    "bmad/workflows/W1_corpus_refresh.md",
    "bmad/workflows/W2_session_prep.md",
    "bmad/workflows/W3_release.md",
    "bmad/checklists/definition_of_done.md",
    "bmad/checklists/session_readiness.md",
    ".github/copilot-instructions.md",
    ".continue/config.yaml",
    ".vscode/settings.json",
    ".vscode/tasks.json",
    "templates/AGENTS.md",
    "templates/feature_list.json",
    "templates/PROGRESS.md",
]

LIASCRIPT_DECKS = [
    "part2_teaching/FILE_A_harness_engineering_liascript.md",
    "part4_unesco_brief/D_liascript_deck_assistants.md",
]

# Any http(s) host that is not one of these in a .py file is a failure. The whole
# package is offline by design, so this check is load-bearing rather than cosmetic.
ALLOWED_NET = re.compile(
    r"https?://(127\.0\.0\.1|localhost|0\.0\.0\.0)(:\d+)?", re.IGNORECASE)
URL_IN_CODE = re.compile(r"[\"'`]https?://[^\"'`\s]+")

# Shapes of direct identifiers that must not survive into an indexed corpus.
LEAK_PATTERNS = [
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("phone", re.compile(r"(?<![\w.])\+\d[\d\s().-]{7,}\d(?![\w.])")),
]

failures: list[str] = []
notes: list[str] = []


def fail(check: str, message: str) -> None:
    failures.append(f"[{check}] {message}")


def walk(extensions: tuple[str, ...], under: str = "") -> list[str]:
    base = os.path.join(ROOT, under)
    found: list[str] = []
    for directory, subdirs, files in os.walk(base):
        subdirs[:] = [d for d in subdirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(extensions):
                found.append(os.path.join(directory, name))
    return sorted(found)


# --- 1. syntax -------------------------------------------------------------
def check_syntax() -> None:
    files = walk((".py",))
    for path in files:
        try:
            with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as sink:
                py_compile.compile(path, cfile=sink.name, doraise=True)
        except py_compile.PyCompileError as error:
            fail("syntax", f"{os.path.relpath(path, ROOT)}: {error.msg.strip()}")
    notes.append(f"syntax: {len(files)} Python file(s) compile")


# --- 2. json ---------------------------------------------------------------
def check_json() -> None:
    files = walk((".json",))
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                json.load(handle)
        except (json.JSONDecodeError, OSError) as error:
            fail("json", f"{os.path.relpath(path, ROOT)}: {error}")
    notes.append(f"json: {len(files)} JSON file(s) parse")


# --- 3. structure ----------------------------------------------------------
def check_structure() -> None:
    for relative in REQUIRED:
        if not os.path.exists(os.path.join(ROOT, relative)):
            fail("structure", f"missing required file: {relative}")
    notes.append(f"structure: {len(REQUIRED)} required file(s) present")


# --- 4. offline ------------------------------------------------------------
def check_offline() -> None:
    checked = 0

    # HTML must not LOAD anything remote. Links in prose are fine; src/href on
    # scripts, styles, images and fonts are not — they break offline use silently.
    remote_asset = re.compile(
        r"""<(?:script|link|img|iframe|source|video|audio)\b[^>]*?"""
        r"""(?:src|href)\s*=\s*["'](https?:|//)""", re.IGNORECASE)
    for path in walk((".html",)):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        for match in remote_asset.finditer(text):
            line = text[:match.start()].count("\n") + 1
            fail("offline", f"{os.path.relpath(path, ROOT)}:{line} loads a remote asset; "
                            f"the page must open with the network off")
        if "localStorage" in text or "sessionStorage" in text:
            fail("offline", f"{os.path.relpath(path, ROOT)}: uses browser storage, "
                            f"which is unavailable in some viewers")
        checked += 1

    for path in walk((".py",)):
        relative = os.path.relpath(path, ROOT)
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue          # comments and doc links are fine
                for match in URL_IN_CODE.findall(line):
                    if not ALLOWED_NET.search(match):
                        fail("offline",
                             f"{relative}:{number} reaches a non-local endpoint: {match}")
        checked += 1
    notes.append(f"offline: {checked} file(s) load nothing remote")


# --- 5. liascript ----------------------------------------------------------
def check_liascript() -> None:
    single_choice = re.compile(r"^\s*\[\((X| )\)\]", re.MULTILINE)
    correct_single = re.compile(r"^\s*\[\(X\)\]", re.MULTILINE)
    multi_choice = re.compile(r"^\s*\[\[(X| )\]\]", re.MULTILINE)
    correct_multi = re.compile(r"^\s*\[\[X\]\]", re.MULTILINE)
    speaker_note = re.compile(r"^--\{\{\d+\}\}--", re.MULTILINE)

    for relative in LIASCRIPT_DECKS:
        path = os.path.join(ROOT, relative)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()

        if not text.lstrip().startswith("<!--"):
            fail("liascript", f"{relative}: missing the LiaScript header comment block")
        if single_choice.search(text) and not correct_single.search(text):
            fail("liascript", f"{relative}: single-choice questions with no [(X)] answer")
        if multi_choice.search(text) and not correct_multi.search(text):
            fail("liascript", f"{relative}: multiple-choice questions with no [[X]] answer")
        if not speaker_note.search(text):
            fail("liascript", f"{relative}: no speaker notes (--{{{{0}}}}-- blocks) found")

        questions = len(correct_single.findall(text)) + len(correct_multi.findall(text))
        notes.append(f"liascript: {relative} — {questions} answered question(s), "
                     f"{len(speaker_note.findall(text))} speaker-note block(s)")


# --- 6. anonymisation ------------------------------------------------------
def check_anonymisation() -> None:
    corpus = os.path.join(ROOT, "part4_unesco_brief", "demo_assistant", "corpus")
    if not os.path.isdir(corpus):
        notes.append("anonymisation: no indexed corpus present, nothing to check")
        return
    leaks = 0
    for name in sorted(os.listdir(corpus)):
        if not name.lower().endswith((".md", ".txt")):
            continue
        with open(os.path.join(corpus, name), "r", encoding="utf-8") as handle:
            text = handle.read()
        for label, pattern in LEAK_PATTERNS:
            for hit in pattern.findall(text):
                fail("anonymisation",
                     f"corpus/{name} still contains an unredacted {label}: {hit}")
                leaks += 1
    if not leaks:
        notes.append("anonymisation: indexed corpus contains no unredacted "
                     "emails or international phone numbers")
    notes.append("anonymisation: NOTE — this checks shapes only. Indirect "
                 "identifiers are not machine-checkable and still need a human.")


# --- 7. knowledge base -----------------------------------------------------
def check_knowledge_base() -> None:
    base = os.path.join(ROOT, "part4_unesco_brief", "demo_assistant")
    kb_path = os.path.join(base, "kb.json")
    corpus = os.path.join(base, "corpus")
    if not os.path.exists(kb_path):
        notes.append("knowledgebase: kb.json absent, nothing to check "
                     "(run `make kb` to build it)")
        return
    try:
        with open(kb_path, "r", encoding="utf-8") as handle:
            kb = json.load(handle)
    except (json.JSONDecodeError, OSError) as error:
        fail("knowledgebase", f"kb.json does not parse: {error}")
        return

    chunks = kb.get("chunks", [])
    if not chunks:
        fail("knowledgebase", "kb.json contains no passages")
        return
    for required_field in ("doc", "section", "text", "id"):
        missing = [c for c in chunks if not c.get(required_field)]
        if missing:
            fail("knowledgebase",
                 f"{len(missing)} passage(s) missing '{required_field}' — "
                 f"without metadata the assistant cannot cite")

    if os.path.isdir(corpus):
        on_disk = {f for f in os.listdir(corpus)
                   if f.lower().endswith((".md", ".txt", ".pdf"))}
        indexed = set(kb.get("documents", []))
        stale = indexed - on_disk
        unindexed = on_disk - indexed
        if stale:
            fail("knowledgebase",
                 f"kb.json indexes document(s) no longer in corpus/: "
                 f"{', '.join(sorted(stale))} — rebuild with `make kb`")
        if unindexed:
            fail("knowledgebase",
                 f"corpus/ contains document(s) not in kb.json: "
                 f"{', '.join(sorted(unindexed))} — rebuild with `make kb`")

    notes.append(f"knowledgebase: {len(chunks)} passage(s) from "
                 f"{len(kb.get('documents', []))} document(s), all carry metadata")


# --- 9. agent surfaces -----------------------------------------------------
def check_agent_surfaces() -> None:
    """The Copilot and Continue configuration is part of the harness, so it is checked.

    Deliberately light: frontmatter presence and offline-only endpoints. Parsing
    YAML would add a dependency, and this package's harness core stays stdlib-only.
    """
    front = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    for folder, suffix, needs in (
        (".github/agents", ".agent.md", ("description:",)),
        (".github/prompts", ".prompt.md", ("description:",)),
        (".github/instructions", ".instructions.md", ("applyTo:",)),
    ):
        directory = os.path.join(ROOT, folder)
        if not os.path.isdir(directory):
            fail("agents", f"missing {folder}/")
            continue
        files = sorted(f for f in os.listdir(directory) if f.endswith(suffix))
        if not files:
            fail("agents", f"{folder}/ contains no {suffix} files")
        for name in files:
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                text = handle.read()
            match = front.match(text)
            if not match:
                fail("agents", f"{folder}/{name}: missing YAML frontmatter")
                continue
            for field in needs:
                if field not in match.group(1):
                    fail("agents", f"{folder}/{name}: frontmatter missing '{field}'")
        notes.append(f"agents: {folder}/ — {len(files)} file(s) with valid frontmatter")

    # Every handoff must name an agent that exists.
    agents_dir = os.path.join(ROOT, ".github", "agents")
    if os.path.isdir(agents_dir):
        declared: set[str] = set()
        for name in os.listdir(agents_dir):
            if not name.endswith(".agent.md"):
                continue
            with open(os.path.join(agents_dir, name), "r", encoding="utf-8") as handle:
                head = front.match(handle.read())
            if head:
                found = re.search(r"^name:\s*(.+)$", head.group(1), re.MULTILINE)
                declared.add(found.group(1).strip() if found else name[:-9])
        for name in os.listdir(agents_dir):
            if not name.endswith(".agent.md"):
                continue
            with open(os.path.join(agents_dir, name), "r", encoding="utf-8") as handle:
                head = front.match(handle.read())
            if not head:
                continue
            for target in re.findall(r"^\s+agent:\s*(.+)$", head.group(1), re.MULTILINE):
                if target.strip() not in declared:
                    fail("agents", f".github/agents/{name}: handoff targets unknown "
                                   f"agent '{target.strip()}'")
        notes.append(f"agents: handoff targets resolve ({len(declared)} agent(s) declared)")

    config = os.path.join(ROOT, ".continue", "config.yaml")
    if not os.path.exists(config):
        fail("agents", "missing .continue/config.yaml")
    else:
        with open(config, "r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                if line.strip().startswith("#"):
                    continue
                for match in re.findall(r"https?://[^\s\"']+", line):
                    if not ALLOWED_NET.search(match):
                        fail("agents", f".continue/config.yaml:{number} non-local "
                                       f"endpoint: {match}")
        notes.append("agents: .continue/config.yaml points only at 127.0.0.1")


# --- 8. links --------------------------------------------------------------
def check_links() -> None:
    link = re.compile(r"\[[^\]]*\]\((?!https?:|mailto:|#)([^)\s]+)\)")
    broken = 0
    for path in walk((".md",)):
        relative = os.path.relpath(path, ROOT)
        directory = os.path.dirname(path)
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, start=1):
                for target in link.findall(line):
                    target = target.split("#")[0]
                    if not target or target.startswith("<"):
                        continue
                    if not os.path.exists(os.path.normpath(os.path.join(directory, target))):
                        fail("links", f"{relative}:{number} broken link: {target}")
                        broken += 1
    if not broken:
        notes.append("links: all relative Markdown links resolve")


# ---------------------------------------------------------------------------

def main() -> int:
    print(f"Verifying package at {ROOT}\n")
    for check in (check_syntax, check_json, check_structure, check_offline,
                  check_liascript, check_anonymisation, check_knowledge_base,
                  check_agent_surfaces, check_links):
        check()

    for note in notes:
        print(f"  ok   {note}")

    if failures:
        print(f"\n{len(failures)} FAILURE(S):\n")
        for failure in failures:
            print(f"  FAIL {failure}")
        print("\nVERIFICATION FAILED. Nothing may be marked `passing` until this "
              "exits 0.")
        return 1

    print("\nAll checks passed. This output is the evidence to paste into "
          "feature_list.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
